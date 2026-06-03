"""Content analysis router — template recommendation API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.template_recommender import (
    RecommendationEngine,
    get_all_templates,
    get_template_by_alias,
)
from models.template import TemplateRecommendation
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


class AnalyzeRequest(BaseModel):
    """Analyze request model."""

    transcript_text: str
    podcast_name: str = ""
    episode_title: str = ""


class AnalyzeResponse(BaseModel):
    """Analyze response model."""

    success: bool
    recommendation: TemplateRecommendation


class TemplatesResponse(BaseModel):
    """Templates list response model."""

    success: bool
    templates: list[dict]


@router.post("/", response_model=AnalyzeResponse)
async def analyze_content(request: AnalyzeRequest):
    """Analyze transcript text and recommend template.

    Args:
        request: Analyze request with transcript text

    Returns:
        Analyze response with template recommendation
    """
    try:
        if not request.transcript_text or len(request.transcript_text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Transcript text is too short (minimum 10 characters)",
            )

        engine = _get_engine()
        recommendation = engine.recommend(request.transcript_text)

        logger.info(
            "Content analyzed",
            podcast=request.podcast_name,
            episode=request.episode_title,
            recommended_template=recommendation.recommended_template,
            confidence=recommendation.confidence,
        )

        return AnalyzeResponse(
            success=True,
            recommendation=recommendation,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/templates", response_model=TemplatesResponse)
async def get_templates():
    """Get all available templates metadata.

    Returns:
        List of template metadata
    """
    try:
        templates = get_all_templates()
        return TemplatesResponse(
            success=True,
            templates=[
                {
                    "alias": t.alias,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "tags": t.tags,
                    "output_format": t.output_format,
                    "is_visual": t.is_visual,
                }
                for t in templates
            ],
        )

    except Exception as e:
        logger.error("Failed to get templates", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get templates: {str(e)}"
        )


@router.get("/templates/{alias}")
async def get_template_detail(alias: str):
    """Get specific template metadata.

    Args:
        alias: Template alias

    Returns:
        Template metadata
    """
    try:
        template = get_template_by_alias(alias)
        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template '{alias}' not found",
            )

        return {
            "success": True,
            "template": {
                "alias": template.alias,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "output_format": template.output_format,
                "is_visual": template.is_visual,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template", alias=alias, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get template: {str(e)}"
        )
