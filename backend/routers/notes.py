"""笔记保存/查看/删除/导出路由。

设计要点：
- POST /api/notes/      保存笔记（前端显式保存或手动创建）
- GET /api/notes/       分页列表（创建时间倒序，列表不含正文）
- GET /api/notes/by-episode/{episode_id}  按 episode_id 查询关联笔记
- GET /api/notes/{note_id}               笔记详情（含正文与转录原文）
- DELETE /api/notes/{note_id}            删除笔记（级联清理配图关联）
- GET /api/notes/{note_id}/export?format=md|txt  导出下载
- GET  /api/notes/{note_id}/images       查询笔记关联配图（空列表不报错）
- POST /api/notes/{note_id}/images       为笔记生成配图并写入关联
- 存储层见 backend/notes_store.py（SQLite WAL 持久化）
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from backend.notes_store import get_notes_db
from core.image_generator import ImageGenerator
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 支持的导出格式
_EXPORT_FORMATS = {"md", "txt"}


class NoteCreate(BaseModel):
    """保存笔记请求模型。"""

    title: str = ""
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    word_count: int = 0
    template: str = ""
    podcast_name: str = ""
    episode_title: str = ""
    episode_id: str | None = None
    transcript_text: str | None = None


class NoteListResponse(BaseModel):
    """笔记列表响应模型（列表项不含正文）。"""

    success: bool = True
    items: list[dict]
    total: int
    limit: int
    offset: int


class NoteResponse(BaseModel):
    """单条笔记响应模型。"""

    success: bool = True
    note: dict


class NoteDeleteResponse(BaseModel):
    """删除笔记响应模型。"""

    success: bool = True
    deleted: bool


class NoteImageGenerateRequest(BaseModel):
    """为笔记生成配图的请求模型（素材取自笔记本身，仅需可选风格）。"""

    style: str = "blue"


class NoteImagesResponse(BaseModel):
    """笔记关联配图响应模型（空列表不报错）。"""

    success: bool = True
    images: list[dict]
    count: int


def _sanitize_filename(title: str, note_id: int) -> str:
    """从标题生成安全文件名：去掉路径分隔符等危险字符，兜底用笔记 id。"""
    cleaned = "".join(
        ch for ch in (title or "").strip() if ch not in r'\/:*?"<>|'
    ).strip()
    if not cleaned:
        cleaned = f"note-{note_id}"
    # 限制长度，避免文件名过长
    return cleaned[:60]


def _render_note(note: dict, fmt: str) -> tuple[str, str]:
    """将笔记渲染为导出文本，返回 (文本, 扩展名)。"""
    title = note.get("title") or "播客笔记"
    content = note.get("content") or ""
    tags = note.get("tags") or []
    meta_parts = []
    if note.get("podcast_name"):
        meta_parts.append(f"播客：{note['podcast_name']}")
    if note.get("episode_title"):
        meta_parts.append(f"单集：{note['episode_title']}")
    if note.get("created_at"):
        meta_parts.append(f"保存时间：{note['created_at']}")

    if fmt == "md":
        lines = [f"# {title}", ""]
        if meta_parts:
            lines.append("  |  ".join(meta_parts))
            lines.append("")
        lines.append(content)
        if tags:
            lines += ["", " ".join(f"#{t.lstrip('#')}" for t in tags if t)]
        text = "\n".join(lines)
    else:  # txt
        lines = [title, "=" * 40, ""]
        if meta_parts:
            lines += ["  |  ".join(meta_parts), ""]
        lines.append(content)
        if tags:
            lines += ["", "标签：" + "、".join(t for t in tags if t)]
        text = "\n".join(lines)
    return text, fmt


@router.post("/", response_model=NoteResponse)
async def create_note(request: NoteCreate):
    """保存一条笔记并返回完整笔记（含自增 id）。"""
    if not (request.content or "").strip() and not (request.title or "").strip():
        raise HTTPException(status_code=422, detail="笔记标题与正文不能同时为空")
    try:
        note = get_notes_db().create_note(
            title=request.title,
            content=request.content,
            tags=request.tags,
            word_count=request.word_count,
            template=request.template,
            podcast_name=request.podcast_name,
            episode_title=request.episode_title,
            episode_id=request.episode_id,
            transcript_text=request.transcript_text,
        )
        logger.info("笔记已保存", note_id=note["id"], title=note["title"])
        return NoteResponse(note=note)
    except Exception as e:  # 存储 failures 返回 500
        logger.error("笔记保存失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"Note save failed: {e}") from e


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    limit: int = Query(default=50, ge=1, le=200, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
):
    """分页查询笔记列表（创建时间倒序，列表项不含正文）。"""
    try:
        result = get_notes_db().list_notes(limit=limit, offset=offset)
        return NoteListResponse(**result)
    except Exception as e:
        logger.error("笔记列表查询失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"Note list failed: {e}") from e


@router.get("/by-episode/{episode_id}", response_model=NoteListResponse)
async def list_notes_by_episode(episode_id: str):
    """按 episode_id 查询关联笔记（含正文，创建时间倒序）。"""
    try:
        items = get_notes_db().get_notes_by_episode(episode_id)
        return NoteListResponse(
            items=items, total=len(items), limit=len(items), offset=0
        )
    except Exception as e:
        logger.error("按单集查询笔记失败", error=str(e), episode_id=episode_id)
        raise HTTPException(status_code=500, detail=f"Note query failed: {e}") from e


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_detail(note_id: int):
    """查询单条笔记详情（含正文与转录原文）。"""
    note = get_notes_db().get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(note=note)


@router.delete("/{note_id}", response_model=NoteDeleteResponse)
async def delete_note(note_id: int):
    """删除一条笔记，不存在时返回 404。"""
    try:
        deleted = get_notes_db().delete_note(note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found")
        logger.info("笔记已删除", note_id=note_id)
        return NoteDeleteResponse(deleted=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("笔记删除失败", error=str(e), note_id=note_id)
        raise HTTPException(status_code=500, detail=f"Note delete failed: {e}") from e


@router.get("/{note_id}/export")
async def export_note(note_id: int, format: str = Query(default="md")):
    """导出笔记为 Markdown / 纯文本下载。

    使用 RFC 5987 的 filename* 编码中文文件名，保证各端正常下载。
    """
    if format not in _EXPORT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format: '{format}' (supported: md, txt)",
        )
    note = get_notes_db().get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    text, ext = _render_note(note, format)
    filename = quote(f"{_sanitize_filename(note['title'], note_id)}.{ext}")
    media_type = (
        "text/markdown; charset=utf-8"
        if ext == "md"
        else "text/plain; charset=utf-8"
    )
    return Response(
        content=text,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=note-{note_id}.{ext}; "
                f"filename*=UTF-8''{filename}"
            )
        },
    )


def _with_url(images: list[dict]) -> list[dict]:
    """给关联记录附加可通过 /images 静态目录访问的 URL 字段。"""
    for item in images:
        item["url"] = f"/images/{item.get('image_name', '')}"
    return images


@router.get("/{note_id}/images", response_model=NoteImagesResponse)
async def list_note_images(note_id: int):
    """查询笔记关联配图（无配图返回空列表，笔记不存在返回 404）。"""
    note = get_notes_db().get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    images = _with_url(get_notes_db().list_note_images(note_id))
    return NoteImagesResponse(images=images, count=len(images))


@router.post("/{note_id}/images", response_model=NoteImagesResponse)
async def generate_note_images(
    note_id: int, request: NoteImageGenerateRequest | None = None
):
    """以笔记标题/正文/标签为素材生成配图并写入关联表。

    生成能力依赖本地 Playwright（HTML 截图渲染），
    不可用时返回 503 与明确错误信息，前端可据此禁用入口。
    """
    note = get_notes_db().get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    style = (request.style if request else "blue") or "blue"

    try:
        structured_content = {
            "hook_title": note.get("title") or "播客笔记",
            "thinking": note.get("content") or "",
            "tags": note.get("tags") or [],
        }
        source_info = {
            "podcast_name": note.get("podcast_name") or "",
            "episode_title": note.get("episode_title") or "",
        }

        generator = ImageGenerator()
        image_paths = await generator.generate_note_images(
            structured_content=structured_content,
            source_info=source_info,
            style=style,
        )

        # 生成器使用固定文件名（cover_*/content_01/summary 等），
        # 多笔记/多次生成会互相覆盖，重命名到笔记专属前缀后再落关联。
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        renamed: list[Path] = []
        for i, path in enumerate(image_paths):
            target = generator.output_dir / (
                f"note_{note_id}_{ts}_{i:02d}_{path.name}"
            )
            path.replace(target)
            renamed.append(target)

        images = get_notes_db().add_note_images(note_id, renamed)
        logger.info(
            "笔记配图生成完成", note_id=note_id, count=len(renamed)
        )
        return NoteImagesResponse(
            images=_with_url(images), count=len(images)
        )
    except Exception as e:  # noqa: BLE001
        logger.error("笔记配图生成失败", note_id=note_id, error=str(e))
        message = str(e) or e.__class__.__name__
        hint = (
            "图片生成能力不可用，请检查 Playwright/Chromium 是否已安装"
            "（playwright install chromium）"
        )
        raise HTTPException(
            status_code=503, detail=f"Image generation unavailable: {message}。{hint}"
        ) from e