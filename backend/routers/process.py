"""Content processing router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.notes_store import get_notes_db
from core.content_processor import ContentProcessor, ContentProcessorError
from core.template_recommender import (
    RecommendationEngine,
    get_template_by_alias,
)
from models.transcript import Transcript
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global recommendation engine instance
_recommendation_engine: RecommendationEngine | None = None


def _get_engine() -> RecommendationEngine:
    """Get or create the recommendation engine singleton."""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


class ProcessRequest(BaseModel):
    """Process request model."""

    transcript_text: str = Field(min_length=1, max_length=2_000_000)
    template: str | None = Field(
        default=None,
        description="Template alias (e.g., v9). If not provided, auto-recommendation will be used.",
    )
    podcast_name: str = ""
    episode_title: str = ""
    allow_auto_recommend: bool = Field(
        default=True,
        description="Whether to allow automatic template recommendation",
    )


class RecommendationInfo(BaseModel):
    """Recommendation information in response."""

    was_recommended: bool
    reason: str
    confidence: float


class ProcessResponse(BaseModel):
    """Process response model."""

    success: bool
    note: dict
    used_template: str
    recommendation_info: RecommendationInfo | None = None
    saved_note_id: int | None = Field(
        default=None,
        description="生成成功后自动保存到笔记库的 id；保存失败时为 None",
    )


# Template alias to full template name mapping
_TEMPLATE_MAP = {
    "v1": "xiaohongshu_note_v1",
    "v2": "xiaohongshu_note_v2",
    "v3": "xiaohongshu_note_v3",
    "v4": "xiaohongshu_note_v4_humanized",
    "v5": "xiaohongshu_note_v5_dry_goods",
    "v6": "xiaohongshu_note_v6_story",
    "v7": "xiaohongshu_note_v7_visual",
    "v7d": "xiaohongshu_note_v7_visual_dense",
    "v8": "xiaohongshu_note_v8_transcript",
    "v9": "xiaohongshu_note_v9_analysis",
}


@router.post("/", response_model=ProcessResponse)
async def process_content(request: ProcessRequest):
    """Process transcript text into Xiaohongshu note.

    Args:
        request: Process request with transcript text and options

    Returns:
        Process response with generated note and template info
    """
    try:
        if not request.transcript_text.strip():
            raise HTTPException(status_code=422, detail="请先输入转录文本")

        # Create a Transcript object from the provided text
        transcript = Transcript(
            episode_title=request.episode_title or "未命名单集",
            podcast_name=request.podcast_name or "未知播客",
            full_text=request.transcript_text,
            segments=[],
        )

        # Determine which template to use
        recommendation_info: RecommendationInfo | None = None
        template_alias: str

        if request.template:
            # User explicitly selected a template
            template_alias = request.template
            logger.info(
                "User selected template",
                template=template_alias,
            )
        elif request.allow_auto_recommend:
            # Auto-recommend based on content features
            engine = _get_engine()
            recommendation = engine.recommend(request.transcript_text)
            template_alias = recommendation.recommended_template
            recommendation_info = RecommendationInfo(
                was_recommended=True,
                reason=recommendation.reason,
                confidence=recommendation.confidence,
            )
            logger.info(
                "Auto-recommended template",
                template=template_alias,
                confidence=recommendation.confidence,
                reason=recommendation.reason,
            )
        else:
            # Default fallback
            template_alias = "v9"
            recommendation_info = RecommendationInfo(
                was_recommended=False,
                reason="使用默认模板（自动推荐已禁用）",
                confidence=0.5,
            )

        # Validate template alias
        template_metadata = get_template_by_alias(template_alias)
        if not template_metadata:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown template alias: '{template_alias}'",
            )

        # Map template alias to full template name
        template_name = _TEMPLATE_MAP.get(template_alias, template_alias)

        # Process the transcript
        def generate():
            return ContentProcessor().process(transcript=transcript, template_name=template_name)
        result = await run_in_threadpool(generate)

        # Convert to response format
        note = {
            "title": result.title or "播客笔记",
            "content": result.content or "",
            "tags": result.tags or [],
            "word_count": result.word_count,
        }

        # 生成成功后自动保存到笔记库（SQLite 持久化）。
        # 入库失败只记 warning，不影响笔记生成的正常返回。
        saved_note_id: int | None = None
        try:
            saved_note = get_notes_db().create_note(
                title=note["title"],
                content=note["content"],
                tags=note["tags"],
                word_count=note["word_count"],
                template=template_alias,
                podcast_name=request.podcast_name or "未知播客",
                episode_title=request.episode_title or "未命名单集",
                episode_id=None,
                transcript_text=request.transcript_text,
            )
            saved_note_id = saved_note["id"]
            logger.info("笔记已自动入库", note_id=saved_note_id)
        except Exception as save_error:
            logger.warning(
                "笔记自动入库失败（不影响生成结果）", error=str(save_error)
            )

        return ProcessResponse(
            success=True,
            note=note,
            used_template=template_alias,
            recommendation_info=recommendation_info,
            saved_note_id=saved_note_id,
        )

    except HTTPException:
        raise
    except ContentProcessorError as e:
        # 输入类错误（如转写文本为空）返回 422，而非 500
        logger.warning("Processing rejected invalid input", error=str(e))
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.error("Processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}") from e
