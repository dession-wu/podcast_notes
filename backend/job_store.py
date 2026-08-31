"""内存 jobs 字典的淘汰机制（P0-3 内存泄漏治理）。

为路由模块的内存 jobs 字典（dict[str, dict]）提供：
- 终态时间记录（finished_at）
- 后台定时清理（超过 TTL 的终态/僵死 job）
- 容量上限保护（超限时优先驱逐终态 job）

接口与原有 dict[str, dict] 结构完全兼容：
jobs 字典本身保持普通 dict，仅在写入与终态时调用本模块钩子。
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

# 终态状态集合
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
# 已完成/失败 job 的最长保留时间（24 小时）
JOB_TTL_SECONDS = 24 * 3600
# 单个 jobs 字典的容量上限
MAX_JOBS = 1000
# 后台清理线程的执行间隔（1 小时）
CLEANUP_INTERVAL_SECONDS = 3600

_lock = threading.Lock()
_registered_stores: dict[str, dict] = {}
_cleanup_thread: threading.Thread | None = None


def register_jobs_dict(name: str, jobs: dict) -> None:
    """注册一个 jobs 字典，纳入后台定时清理。

    首次注册时启动清理守护线程（进程内仅启动一次）。
    """
    global _cleanup_thread
    with _lock:
        _registered_stores[name] = jobs
        if _cleanup_thread is None or not _cleanup_thread.is_alive():
            _cleanup_thread = threading.Thread(
                target=_cleanup_loop, name="job-store-cleanup", daemon=True
            )
            _cleanup_thread.start()


def add_job(jobs: dict, job_id: str, payload: dict) -> None:
    """写入新 job，并在超出容量上限时先驱逐旧条目。"""
    with _lock:
        if len(jobs) >= MAX_JOBS:
            _evict_for_capacity(jobs)
        jobs[job_id] = payload


def mark_job_finished(jobs: dict, job_id: str) -> None:
    """在 job 进入终态时记录完成时间（幂等）。"""
    with _lock:
        job = jobs.get(job_id)
        if job is not None and "finished_at" not in job:
            job["finished_at"] = time.time()


def evict_expired(jobs: dict, ttl: float = JOB_TTL_SECONDS) -> int:
    """清理超过 TTL 的 job，返回清理数量。

    清理对象：
    - 终态且 finished_at 超过 TTL
    - 终态但缺少 finished_at（按 created_at/start_time 兜底）
    - 非终态但已超过 TTL 的僵死 job（worker 异常退出导致）
    """
    now = time.time()
    expired: list[str] = []
    with _lock:
        for job_id, job in jobs.items():
            status = job.get("status")
            finished_at = job.get("finished_at")
            created = finished_at or job.get("created_at") or job.get("start_time")
            if created is None:
                continue
            age = now - created
            if status in TERMINAL_STATUSES:
                if age > ttl:
                    expired.append(job_id)
            elif age > ttl:
                # 僵死 job（长时间无终态），同样清理
                expired.append(job_id)
                logger.warning(
                    "清理僵死 job（长时间未进入终态） job_id=%s status=%s age_seconds=%s",
                    job_id, status, round(age),
                )
        for job_id in expired:
            jobs.pop(job_id, None)
    if expired:
        logger.info("jobs 淘汰清理完成 removed=%d remaining=%d", len(expired), len(jobs))
    return len(expired)


def _evict_for_capacity(jobs: dict) -> None:
    """容量超限时驱逐：优先终态（最旧），其次按创建时间最旧。"""
    terminal = [
        (job.get("finished_at") or job.get("created_at") or job.get("start_time") or 0, job_id)
        for job_id, job in jobs.items()
        if job.get("status") in TERMINAL_STATUSES
    ]
    if terminal:
        terminal.sort()
        _, oldest = terminal[0]
        jobs.pop(oldest, None)
        logger.warning("jobs 容量超限，驱逐最旧终态 job job_id=%s", oldest)
        return
    all_jobs = [
        (job.get("created_at") or job.get("start_time") or 0, job_id)
        for job_id, job in jobs.items()
    ]
    all_jobs.sort()
    if all_jobs:
        _, oldest = all_jobs[0]
        jobs.pop(oldest, None)
        logger.warning("jobs 容量超限且无终态可驱逐，驱逐最旧 job job_id=%s", oldest)


def _cleanup_loop() -> None:
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            with _lock:
                stores = dict(_registered_stores)
            for name, jobs in stores.items():
                removed = evict_expired(jobs)
                if removed:
                    logger.info("后台清理 jobs 字典 store=%s removed=%d", name, removed)
        except Exception:  # noqa: BLE001 清理线程不能因单次异常退出
            logger.exception("jobs 后台清理线程异常")