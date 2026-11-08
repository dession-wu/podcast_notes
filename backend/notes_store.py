"""笔记持久化存储（SQLite）— 保存/查看/删除/导出笔记的存取层。

设计要点（参考 persistent_jobs.py 的成熟模式）：
- 单连接 + 全局锁（跨线程安全），WAL 模式，写入开销低。
- 数据库路径可用环境变量 PODCAST_NOTES_NOTES_DB 覆盖，
  默认项目 data/notes.sqlite3。
- 存储失败（磁盘满/损坏等）抛出异常，由调用方（routers/process.py
  自动入库处）捕获并降级为 warning，不影响笔记生成的正常返回。
- tags 以 JSON 文本存储，读取时反序列化为列表。
- 时间统一存储 ISO8601 本地时间字符串，列表按创建时间倒序。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 笔记数据库文件路径：环境变量可覆盖，默认项目 data/ 目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
from config import settings
_DEFAULT_DB_PATH = settings.data_dir / "notes.sqlite3"
NOTES_DB_PATH = Path(os.environ.get("PODCAST_NOTES_NOTES_DB", str(_DEFAULT_DB_PATH)))

# 列表接口默认分页上限
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class NotesDB:
    """SQLite 存取层：单连接 + 全局锁（跨线程安全），WAL 模式。"""

    _DDL = """
    CREATE TABLE IF NOT EXISTS notes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL DEFAULT '',
        content         TEXT NOT NULL DEFAULT '',
        tags            TEXT NOT NULL DEFAULT '[]',
        word_count      INTEGER NOT NULL DEFAULT 0,
        template        TEXT NOT NULL DEFAULT '',
        podcast_name    TEXT NOT NULL DEFAULT '',
        episode_title   TEXT NOT NULL DEFAULT '',
        episode_id      TEXT,
        transcript_text TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    )
    """

    _DDL_NOTE_IMAGES = """
    CREATE TABLE IF NOT EXISTS note_images (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id     INTEGER NOT NULL,
        image_path  TEXT NOT NULL,
        image_name  TEXT NOT NULL,
        created_at  TEXT NOT NULL
    )
    """

    _COLUMNS = (
        "id, title, content, tags, word_count, template, "
        "podcast_name, episode_title, episode_id, transcript_text, "
        "created_at, updated_at"
    )

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False, timeout=10.0
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(self._DDL)
            self._conn.execute(self._DDL_NOTE_IMAGES)
            self._conn.commit()
        self._db_path = db_path
        logger.info("笔记持久化存储就绪 db=%s", db_path)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _now() -> str:
        from datetime import datetime

        return datetime.now().isoformat(timespec="seconds")

    def _row_to_note(self, row: sqlite3.Row) -> dict[str, Any]:
        """将数据库行转换为对外的笔记 dict（tags 反序列化为列表）。"""
        note = dict(row)
        try:
            tags = json.loads(note.get("tags") or "[]")
            if not isinstance(tags, list):
                tags = []
        except (TypeError, ValueError):
            tags = []
        note["tags"] = tags
        return note

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #

    def create_note(
        self,
        *,
        title: str = "",
        content: str = "",
        tags: list[str] | None = None,
        word_count: int = 0,
        template: str = "",
        podcast_name: str = "",
        episode_title: str = "",
        episode_id: str | None = None,
        transcript_text: str | None = None,
    ) -> dict[str, Any]:
        """插入一条笔记，返回含自增 id 的完整笔记 dict。"""
        now = self._now()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        # 转录原文可能很长，仅保存前 5000 字作为溯源摘要，避免库体积膨胀
        transcript_saved = (
            transcript_text[:5000] if transcript_text else None
        )
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO notes (title, content, tags, word_count, "
                "template, podcast_name, episode_title, episode_id, "
                "transcript_text, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    title or "播客笔记",
                    content or "",
                    tags_json,
                    int(word_count or 0),
                    template or "",
                    podcast_name or "",
                    episode_title or "",
                    episode_id,
                    transcript_saved,
                    now,
                    now,
                ),
            )
            self._conn.commit()
            note_id = cursor.lastrowid
        return self.get_note(note_id)  # type: ignore[return-value]

    def list_notes(
        self,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        include_content: bool = False,
    ) -> dict[str, Any]:
        """分页查询笔记列表（创建时间倒序）。

        Args:
            limit: 每页条数，超过 MAX_PAGE_SIZE 时截断
            offset: 偏移量
            include_content: 列表默认不返回正文与转录原文（体积大），
                详情接口才会返回；置 True 时全部返回。

        Returns:
            {"items": [...], "total": 总条数, "limit": ..., "offset": ...}
        """
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        offset = max(0, offset)
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM notes"
            ).fetchone()["cnt"]
            rows = self._conn.execute(
                "SELECT "
                + (
                    self._COLUMNS
                    if include_content
                    else "id, title, tags, word_count, template, "
                    "podcast_name, episode_title, episode_id, created_at, "
                    "updated_at"
                )
                + " FROM notes ORDER BY created_at DESC, id DESC "
                "LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        items = []
        for row in rows:
            note = self._row_to_note(row)
            if not include_content:
                note.pop("transcript_text", None)
            items.append(note)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_note(self, note_id: int) -> dict[str, Any] | None:
        """按 id 查询单条笔记（含正文与转录原文），不存在返回 None。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT " + self._COLUMNS + " FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        return self._row_to_note(row) if row else None

    def get_notes_by_episode(self, episode_id: str) -> list[dict[str, Any]]:
        """按 episode_id 查询关联笔记（创建时间倒序，含正文）。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT " + self._COLUMNS + " FROM notes "
                "WHERE episode_id = ? ORDER BY created_at DESC, id DESC",
                (episode_id,),
            ).fetchall()
        return [self._row_to_note(row) for row in rows]

    def delete_note(self, note_id: int) -> bool:
        """按 id 删除笔记，返回是否删除成功（存在即成功）。

        同时级联删除该笔记的图片关联记录（不删图片文件本身）。
        """
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM notes WHERE id = ?", (note_id,)
            )
            if cursor.rowcount:
                self._conn.execute(
                    "DELETE FROM note_images WHERE note_id = ?", (note_id,)
                )
            self._conn.commit()
            deleted = cursor.rowcount
        return bool(deleted)

    # ------------------------------------------------------------------ #
    # 笔记配图关联（note_images）
    # ------------------------------------------------------------------ #

    def add_note_images(
        self, note_id: int, image_paths: list[Path]
    ) -> list[dict[str, Any]]:
        """批量写入笔记配图关联，返回插入后的关联记录列表。"""
        now = self._now()
        rows = [
            (note_id, str(p), p.name, now) for p in image_paths if p
        ]
        if not rows:
            return []
        with self._lock:
            self._conn.executemany(
                "INSERT INTO note_images (note_id, image_path, image_name, "
                "created_at) VALUES (?, ?, ?, ?)",
                rows,
            )
            self._conn.commit()
        return self.list_note_images(note_id)

    def list_note_images(self, note_id: int) -> list[dict[str, Any]]:
        """按笔记 id 查询关联配图（写入顺序，即 id 升序），无关联返回空列表。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, note_id, image_path, image_name, created_at "
                "FROM note_images WHERE note_id = ? ORDER BY id ASC",
                (note_id,),
            ).fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------- #
# 进程级单例：所有路由共享同一个 NotesDB 实例
# ---------------------------------------------------------------------- #

_notes_db: NotesDB | None = None
_notes_db_lock = threading.Lock()


def get_notes_db() -> NotesDB:
    """获取（惰性创建）进程级 NotesDB 单例。"""
    global _notes_db
    if _notes_db is None:
        with _notes_db_lock:
            if _notes_db is None:
                _notes_db = NotesDB(NOTES_DB_PATH)
    return _notes_db
