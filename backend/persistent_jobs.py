"""任务持久化存储（SQLite）— 服务重启后任务状态可恢复。

设计要点：
- 对 routers 透明：PersistentJobsDict / _JobPayload 均为 dict 子类，
  现有代码 jobs[task_id][...] = ... / jobs.pop(...) 等用法无需改动。
- 写入时机：状态/结果/错误等关键字段立即写盘；progress 等高频进度
  字段按 FLUSH_INTERVAL 节流写（脏标记 + 兜底刷盘线程），避免每毫秒落盘。
- SQLite WAL 模式：读写并发安全，写入开销低。
- 重启恢复：实例化时从 SQLite 加载未过期任务；TTL/容量上限语义与
  job_store 保持一致；非终态任务（重启后 worker 已丢失）标记为 failed。
- 持久化失败（磁盘满/损坏等）仅记录日志，不影响内存语义。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 任务数据库文件路径：环境变量可覆盖，默认项目 data/ 目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "jobs.sqlite3"
JOB_DB_PATH = Path(os.environ.get("PODCAST_NOTES_JOBS_DB", str(_DEFAULT_DB_PATH)))

# 进度类高频字段的节流间隔（秒）：到期才写盘，期间仅记脏标记
FLUSH_INTERVAL_SECONDS = 1.0
# 兜底刷盘线程间隔（秒）：保证脏任务最长延迟落盘时间有界
FLUSH_LOOP_SECONDS = 5.0
# 进度类字段集合：只节流不立即写
_THROTTLED_KEYS = {"progress", "downloaded_bytes", "total_bytes", "stage"}

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
JOB_TTL_SECONDS = 24 * 3600
MAX_JOBS = 1000

# 重启恢复时对非终态任务的标注
INTERRUPTED_ERROR = "服务重启导致任务中断，请重新发起"
INTERRUPTED_CATEGORY = "server_restarted"


class _JobDB:
    """SQLite 存取层：单连接 + 全局锁（跨线程安全），WAL 模式。"""

    _DDL = """
    CREATE TABLE IF NOT EXISTS jobs (
        store      TEXT NOT NULL,
        task_id    TEXT NOT NULL,
        payload    TEXT NOT NULL,
        updated_at REAL NOT NULL,
        PRIMARY KEY (store, task_id)
    )
    """

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False, timeout=10.0
        )
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(self._DDL)
            self._conn.commit()
        self._db_path = db_path
        logger.info("任务持久化存储就绪 db=%s", db_path)

    def upsert(self, store: str, task_id: str, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs (store, task_id, payload, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(store, task_id) DO UPDATE SET "
                "payload=excluded.payload, updated_at=excluded.updated_at",
                (store, task_id, data, time.time()),
            )
            self._conn.commit()

    def delete(self, store: str, task_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM jobs WHERE store = ? AND task_id = ?", (store, task_id)
            )
            self._conn.commit()

    def load_store(self, store: str) -> dict[str, dict]:
        """加载某个 store 的全部任务（原始 payload，不做 TTL 过滤）。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT task_id, payload FROM jobs WHERE store = ?", (store,)
            ).fetchall()
        result = {}
        for task_id, data in rows:
            try:
                result[task_id] = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                logger.warning("持久化任务载荷解析失败，跳过 store=%s task_id=%s", store, task_id)
        return result

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# 进程级单例：多个 router 共享同一个数据库文件
_db_instance: _JobDB | None = None
_db_lock = threading.Lock()
# 全部已注册的持久化 dict（供兜底刷盘线程扫描脏任务）
_persistent_dicts: list["PersistentJobsDict"] = []
_flush_thread: threading.Thread | None = None


def _get_db() -> _JobDB:
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = _JobDB(JOB_DB_PATH)
    return _db_instance


def _start_flush_thread() -> None:
    """启动兜底刷盘线程（进程内仅一次）：定期把脏任务的节流字段落盘。"""
    global _flush_thread
    if _flush_thread is not None and _flush_thread.is_alive():
        return
    _flush_thread = threading.Thread(
        target=_flush_loop, name="job-store-flush", daemon=True
    )
    _flush_thread.start()


def _flush_loop() -> None:
    while True:
        time.sleep(FLUSH_LOOP_SECONDS)
        try:
            for store in list(_persistent_dicts):
                store.flush_dirty()
        except Exception:  # noqa: BLE001 刷盘线程不能因单次异常退出
            logger.exception("任务持久化兜底刷盘线程异常")


class _JobPayload(dict):
    """job 载荷 dict 子类：字段写入时触发持久化（进度类节流）。"""

    __slots__ = ("_owner", "_task_id", "_dirty", "_last_flush")

    def __init__(self, owner: "PersistentJobsDict", task_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._task_id = task_id
        self._dirty = False
        self._last_flush = 0.0

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key in _THROTTLED_KEYS:
            self._dirty = True
            now = time.time()
            if now - self._last_flush >= FLUSH_INTERVAL_SECONDS:
                self.flush()
        else:
            # 状态/结果/错误/finished_at 等关键字段：立即写盘
            self.flush()

    def update(self, *args, **kwargs):  # type: ignore[override]
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def flush(self) -> None:
        """将当前载荷写盘（失败仅记日志，不影响内存语义）。"""
        self._dirty = False
        self._last_flush = time.time()
        try:
            _get_db().upsert(self._owner.store_name, self._task_id, self)
        except Exception:  # noqa: BLE001 持久化失败不能影响业务
            logger.exception(
                "任务持久化写入失败 store=%s task_id=%s", self._owner.store_name, self._task_id
            )


class PersistentJobsDict(dict):
    """jobs dict 子类：对外与普通 dict 完全兼容，落库/恢复对 routers 透明。"""

    def __init__(self, store_name: str):
        super().__init__()
        self.store_name = store_name
        self._load_from_db()
        with _db_lock:
            _persistent_dicts.append(self)
            _start_flush_thread()

    # ------------------------------------------------------------------
    # 写路径：新增/覆盖任务时包装为可持久化载荷并立即写盘
    # ------------------------------------------------------------------
    def __setitem__(self, task_id: str, payload: dict) -> None:
        if not isinstance(payload, _JobPayload):
            payload = _JobPayload(self, task_id, payload)
        super().__setitem__(task_id, payload)
        payload.flush()

    def setdefault(self, key, default=None):  # type: ignore[override]
        if key in self:
            return self[key]
        if isinstance(default, dict):
            self[key] = default
            return self[key]
        raise TypeError("PersistentJobsDict 仅支持 dict 载荷")

    # ------------------------------------------------------------------
    # 删除路径：同步删除数据库行
    # ------------------------------------------------------------------
    def __delitem__(self, task_id: str) -> None:
        super().__delitem__(task_id)
        self._db_delete(task_id)

    def pop(self, task_id: str, *default):  # type: ignore[override]
        existed = task_id in self
        if default and not existed:
            return default[0]
        value = super().pop(task_id)
        if existed:
            self._db_delete(task_id)
        return value

    def clear(self) -> None:  # type: ignore[override]
        for task_id in list(self.keys()):
            self._db_delete(task_id)
        super().clear()

    # ------------------------------------------------------------------
    # 恢复与兜底
    # ------------------------------------------------------------------
    def _load_from_db(self) -> None:
        """启动恢复：加载未过期任务；非终态任务标记为中断失败。"""
        raw = _get_db().load_store(self.store_name)
        now = time.time()
        restored, dropped, interrupted = 0, 0, 0
        # 按创建时间从新到旧，应用容量上限
        def _created(job: dict) -> float:
            return job.get("created_at") or job.get("start_time") or 0

        ordered = sorted(raw.items(), key=lambda kv: _created(kv[1]), reverse=True)
        for task_id, job in ordered[:MAX_JOBS]:
            status = job.get("status")
            age = now - (job.get("finished_at") or _created(job) or now)
            if age > JOB_TTL_SECONDS:
                dropped += 1
                self._db_delete(task_id)
                continue
            if status not in TERMINAL_STATUSES:
                # 重启后原 worker 线程已丢失，任务无法推进：标记失败
                job["status"] = "failed"
                job["error"] = INTERRUPTED_ERROR
                job["error_category"] = INTERRUPTED_CATEGORY
                job["finished_at"] = now
                interrupted += 1
                was_interrupted = True
            else:
                was_interrupted = False
            payload = _JobPayload(self, task_id, job)
            dict.__setitem__(self, task_id, payload)
            if was_interrupted:
                payload.flush()
            restored += 1
        for task_id, _ in ordered[MAX_JOBS:]:
            dropped += 1
            self._db_delete(task_id)
        if restored or dropped or interrupted:
            logger.info(
                "任务持久化恢复完成 store=%s restored=%d interrupted=%d dropped=%d",
                self.store_name, restored, interrupted, dropped,
            )

    def flush_dirty(self) -> None:
        """将所有脏（节流未落盘）任务写盘。"""
        for task_id, payload in self.items():
            if isinstance(payload, _JobPayload) and payload._dirty:
                payload.flush()

    def _db_delete(self, task_id: str) -> None:
        try:
            _get_db().delete(self.store_name, task_id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "任务持久化删除失败 store=%s task_id=%s", self.store_name, task_id
            )