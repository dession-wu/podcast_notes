"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter

from config import settings
from services.llm_service import LLMService

router = APIRouter()


@router.get("/")
async def health_check():
    """Check API health and service status."""
    # Check LLM service
    llm_status = "unknown"
    try:
        llm = LLMService()
        llm_status = "connected" if llm.provider != "unknown" else "not_configured"
    except Exception:
        llm_status = "error"

    # Check PodcastIndex config
    podcast_index_status = (
        "configured"
        if settings.podcastindex_api_key and settings.podcastindex_api_secret
        else "not_configured"
    )

    # Check STT config
    stt_status = "configured" if settings.stt_provider else "not_configured"

    return {
        "status": "ok",
        "version": "0.1.0",
        "services": {
            "llm": llm_status,
            "podcast_search": podcast_index_status,
            "stt": stt_status,
        },
    }
