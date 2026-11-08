"""Persist the existing settings form without returning credentials to the browser."""
from __future__ import annotations

import json
import os
import tempfile
import threading

from pydantic import BaseModel, Field
from cryptography.fernet import Fernet

def _credential_box():
    keyfile = os.environ.get('TENANT_CREDENTIAL_FILE')
    return Fernet(open(keyfile, 'rb').read()) if keyfile else None

from config.settings import settings, LLMProvider, STTProvider

_lock = threading.RLock()
CONFIG_PATH = settings.data_dir / "config" / "application.json"
_FIELDS = {
    "default_llm_provider", "stt_provider", "podcastindex_api_key",
    "podcastindex_api_secret", "openai_api_key", "anthropic_api_key", "elevenlabs_api_key",
}


class ApplicationSettingsRequest(BaseModel):
    llm_provider: LLMProvider
    stt_engine: STTProvider
    podcastindex_key: str = Field(default="", max_length=4096)
    podcastindex_secret: str = Field(default="", max_length=4096)
    llm_api_key: str = Field(default="", max_length=4096)
    stt_api_key: str = Field(default="", max_length=4096)


def _read() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    raw = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    if isinstance(raw, dict) and 'encrypted' in raw:
        return json.loads(_credential_box().decrypt(raw['encrypted'].encode()))
    return raw


def _apply(data: dict) -> None:
    for key, value in data.items():
        if key in _FIELDS:
            if key == "default_llm_provider":
                value = LLMProvider(value)
            elif key == "stt_provider":
                value = STTProvider(value)
            setattr(settings, key, value)


def load_application_settings() -> None:
    with _lock:
        _apply(_read())
        if os.environ.get('PODCAST_TENANT_WORKER') == '1':
            settings.openai_api_key = os.environ.get('OPENAI_API_KEY', '')
            settings.default_llm_provider = LLMProvider.OPENAI
            settings.stt_provider = STTProvider.ELEVENLABS


def public_settings() -> dict:
    provider = settings.default_llm_provider.value
    return {
        "llm_provider": provider,
        "stt_engine": settings.stt_provider.value,
        "configured": {
            "podcastindex_key": bool(settings.podcastindex_api_key),
            "podcastindex_secret": bool(settings.podcastindex_api_secret),
            "llm_api_key": bool(getattr(settings, f"{provider}_api_key", None)),
            "stt_api_key": bool(settings.elevenlabs_api_key) if settings.stt_provider == STTProvider.ELEVENLABS else False,
        },
    }


def save_application_settings(request: ApplicationSettingsRequest) -> dict:
    if request.stt_api_key.strip() and request.stt_engine != STTProvider.ELEVENLABS:
        raise ValueError("所选本地转录引擎不使用 API Key，请清空此项后保存")
    with _lock:
        data = _read()
        data.update(default_llm_provider=request.llm_provider.value, stt_provider=request.stt_engine.value)
        credentials = {
            "podcastindex_api_key": request.podcastindex_key,
            "podcastindex_api_secret": request.podcastindex_secret,
            "elevenlabs_api_key": request.stt_api_key,
        }
        if request.llm_provider != LLMProvider.OLLAMA:
            credentials[f"{request.llm_provider.value}_api_key"] = request.llm_api_key
        # Empty credential fields preserve existing configuration.
        data.update({key: value.strip() for key, value in credentials.items() if value.strip()})
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CONFIG_PATH.parent, delete=False) as stream:
                temporary = stream.name
                box = _credential_box()
                stored = {'encrypted': box.encrypt(json.dumps(data).encode()).decode()} if box else data
                json.dump(stored, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, CONFIG_PATH)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        _apply(data)
        return public_settings()

