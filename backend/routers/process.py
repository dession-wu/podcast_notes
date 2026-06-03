"""Content processing router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.content_processor import ContentProcessor
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

    transcript_text: str
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
        processor = ContentProcessor()

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
        result = processor.process(
            transcript=transcript,
            template_name=template_name,
        )

        # Convert to response format
        note = {
            "title": result.title or "播客笔记",
            "content": result.content or "",
            "tags": result.tags or [],
            "word_count": result.word_count,
        }

        return ProcessResponse(
            success=True,
            note=note,
            used_template=template_alias,
            recommendation_info=recommendation_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
