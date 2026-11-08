"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter

from config import settings
from importlib.util import find_spec

router = APIRouter()


@router.get("/")
async def health_check():
    """Check API health and service status."""
    # Check LLM service
    provider = settings.default_llm_provider.value
    llm_status = "configured" if provider == "ollama" or bool(getattr(settings, f"{provider}_api_key", None)) else "not_configured"

    # Check PodcastIndex config
    podcast_index_status = (
        "configured"
        if settings.podcastindex_api_key and settings.podcastindex_api_secret
        else "not_configured"
    )

    # Check STT config
    modules = {"whisper": "whisper", "faster-whisper": "faster_whisper", "sensevoice": "funasr"}
    engine = settings.stt_provider.value
    stt_status = "configured" if (find_spec(modules[engine]) is not None if engine in modules else settings.is_elevenlabs_configured) else "not_configured"

    return {
        "status": "ok",
        "version": "0.1.0",
        "services": {
            "llm": llm_status,
            "podcast_search": podcast_index_status,
            "stt": stt_status,
        },
    }
