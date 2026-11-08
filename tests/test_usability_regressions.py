"""Runtime regressions; run with DATA_DIR/TEMP_DIR set to an isolated directory."""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import application_settings as application
from backend.config.download_settings import DownloadSettingsManager, DownloadSettingsModel
from backend.routers import library, images, process, transcribe
from config import settings
from core.image_generator import ImageGenerator


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "podcast_notes_api_key", "regression-key")
    monkeypatch.setattr(settings, "podcast_notes_allow_anonymous", False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(application, "CONFIG_PATH", tmp_path / "application.json")
    with TestClient(app, headers={"X-API-Key": "regression-key"}) as session:
        yield session


def test_library_keeps_transcripts_and_images_when_audio_directory_changes(client, monkeypatch, tmp_path):
    audio = tmp_path / "custom-downloads"
    audio.mkdir()
    (audio / "测试.mp3").write_bytes(b"audio")
    transcript = settings.transcript_dir / "增长100% #提问.md"
    transcript.write_text("原文：100% 值得保留", encoding="utf-8")
    (settings.transcript_dir / "metadata.json").write_text("{}")
    image_dir = settings.output_dir / "images"
    image_dir.mkdir()
    (image_dir / "cover.png").write_bytes(b"image")
    manager = DownloadSettingsManager(tmp_path / "download.json")
    manager.save(DownloadSettingsModel(custom_download_dir=str(audio)))
    monkeypatch.setattr(library, "download_settings_manager", manager)
    data = client.get("/api/library/files").json()
    assert data["type_counts"] == {"audio": 1, "transcript": 1, "image": 1}
    filtered = client.get("/api/library/files?type=audio").json()
    assert filtered["type_counts"] == data["type_counts"]
    assert filtered["total"] == 1
    item = next(item for item in data["files"] if item["type"] == "transcript")
    from urllib.parse import quote
    content = client.get("/api/library/transcript-content/" + quote(item["id"], safe=""))
    assert content.status_code == 200
    assert content.json()["content"] == "原文：100% 值得保留"
    assert client.request("DELETE", "/api/library/files", json={"file_path": str(tmp_path / "application.json")}).status_code in {403, 404}


def test_settings_persist_without_echoing_or_erasing_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "default_llm_provider", settings.default_llm_provider)
    monkeypatch.setattr(settings, "stt_provider", settings.stt_provider)
    monkeypatch.setattr(settings, "openai_api_key", None)
    payload = {"llm_provider": "openai", "stt_engine": "whisper", "llm_api_key": "test-secret-value"}
    response = client.put("/api/settings/application", json=payload)
    assert response.status_code == 200
    assert "test-secret-value" not in response.text
    assert response.json()["configured"]["llm_api_key"] is True
    assert application.CONFIG_PATH.stat().st_mode & 0o077 == 0
    assert json.loads(application.CONFIG_PATH.read_text())["openai_api_key"] == "test-secret-value"
    payload["llm_api_key"] = ""
    assert client.put("/api/settings/application", json=payload).status_code == 200
    assert settings.openai_api_key == "test-secret-value"
    settings.openai_api_key = None
    application.load_application_settings()
    assert settings.openai_api_key == "test-secret-value"
    payload["llm_provider"] = "invalid-provider"
    assert client.put("/api/settings/application", json=payload).status_code == 422


def test_failed_settings_write_does_not_apply(client, monkeypatch):
    original = settings.default_llm_provider
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(application.os, "replace", fail)
    response = client.put("/api/settings/application", json={"llm_provider": "anthropic", "stt_engine": "whisper"})
    assert response.status_code == 500
    assert settings.default_llm_provider == original
    assert not application.CONFIG_PATH.exists()


def test_path_validation_never_removes_existing_write_test(tmp_path):
    existing = tmp_path / ".write_test"
    existing.write_text("user data")
    manager = DownloadSettingsManager(tmp_path / "settings.json")
    assert manager.validate_path(str(tmp_path))["valid"]
    assert existing.read_text() == "user data"
    assert not manager.validate_path("")["valid"]
    assert not manager.validate_path("relative/path")["valid"]


def test_invalid_input_is_rejected_before_model_initialization(client, monkeypatch):
    def unexpected():
        raise AssertionError("LLM should not be initialized")
    monkeypatch.setattr(process, "ContentProcessor", unexpected)
    assert client.post("/api/process/", json={"transcript_text": "   "}).status_code == 422
    assert client.post("/api/process/", json={"transcript_text": "原文", "template": "invalid"}).status_code == 400


def test_images_have_content_and_report_background_failure(client, monkeypatch):
    received = []
    async def fail(self, **kwargs):
        received.append(kwargs["structured_content"])
        raise RuntimeError("test renderer unavailable")
    monkeypatch.setattr(ImageGenerator, "generate_note_images", fail)
    text = "完整保留正文" * 100
    response = client.post("/api/images/", json={"title": "测试", "content": text})
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    result = client.get("/api/images/" + response.json()["task_id"]).json()
    assert result["status"] == "failed"
    assert "renderer unavailable" in result["error"]
    from backend.persistent_jobs import PersistentJobsDict
    restored = PersistentJobsDict("images")
    assert restored[response.json()["task_id"]]["status"] == "failed"
    assert "".join(point["content"] for point in received[0]["key_points"]) == text


def test_distinct_image_generations_do_not_overwrite_and_escape_text(tmp_path, monkeypatch):
    async def render(self, html, destination):
        assert "<script>" not in html
        destination.write_text(html)
    monkeypatch.setattr(ImageGenerator, "_html_to_image", render)
    async def run():
        return await asyncio.gather(*[
            ImageGenerator(tmp_path).generate_cover("<script>alert(1)</script>", "测试", "单集") for _ in range(2)
        ])
    paths = asyncio.run(run())
    assert paths[0] != paths[1]
    assert all(path.exists() for path in paths)


def test_upload_rejects_empty_unsupported_and_oversized_files(client, monkeypatch):
    monkeypatch.setattr(transcribe, "MAX_FILE_SIZE_MB", 0.000001)
    assert client.post("/api/transcribe/", files={"audio": ("test.exe", b"test")}).status_code == 415
    assert client.post("/api/transcribe/", files={"audio": ("test.wav", b"")}).status_code == 400
    assert client.post("/api/transcribe/", files={"audio": ("test.wav", b"too large")}).status_code == 413
    assert not list(settings.audio_download_dir.glob("*.wav"))


def test_business_api_still_requires_api_key(client):
    assert client.get("/api/settings/application", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/health/", headers={"X-API-Key": "wrong"}).status_code == 200


def test_processing_saves_and_exports_successful_result(client, monkeypatch):
    from types import SimpleNamespace
    class Processor:
        def process(self, **kwargs):
            return SimpleNamespace(title="测试笔记", content="第一条观点\n第二条观点", tags=["测试"], word_count=10)
    monkeypatch.setattr(process, "ContentProcessor", Processor)
    response = client.post("/api/process/", json={"transcript_text": "测试原文", "template": "v9"})
    assert response.status_code == 200
    note_id = response.json()["saved_note_id"]
    assert isinstance(note_id, int)
    assert client.get(f"/api/notes/{note_id}").json()["note"]["content"] == "第一条观点\n第二条观点"
    exported = client.get(f"/api/notes/{note_id}/export?format=md")
    assert exported.status_code == 200
    assert "第一条观点" in exported.text
    assert "filename*=UTF-8''" in exported.headers["content-disposition"]
    assert client.delete(f"/api/notes/{note_id}").status_code == 200


def test_transcription_respects_selected_engine_and_publishes_complete_result(client, monkeypatch, tmp_path):
    from config.settings import STTProvider
    from models.transcript import Transcript
    selected = []
    class Transcriber:
        def __init__(self, provider):
            selected.append(provider)
        def transcribe(self, episode):
            return Transcript(episode_title=episode.title, full_text="完整测试原文", stt_provider="faster-whisper")
    monkeypatch.setattr(settings, "stt_provider", STTProvider.FASTER_WHISPER)
    monkeypatch.setattr(transcribe, "Transcriber", Transcriber)
    monkeypatch.setattr(transcribe, "get_audio_duration", lambda path: 1)
    task_id = "test-selected-engine"
    transcribe.jobs[task_id] = {"status": "pending", "result": None, "estimate": None}
    transcribe._do_transcription(task_id, tmp_path / "test.wav", "测试")
    assert selected == [STTProvider.FASTER_WHISPER]
    assert transcribe.jobs[task_id]["status"] == "completed"
    assert transcribe.jobs[task_id]["result"]["text"] == "完整测试原文"


def test_model_initialization_does_not_block_health_requests(client, monkeypatch):
    import threading
    import time
    import httpx
    from types import SimpleNamespace
    started = threading.Event()
    class Processor:
        def __init__(self):
            started.set()
            time.sleep(0.3)
        def process(self, **kwargs):
            return SimpleNamespace(title="并发测试", content="测试内容", tags=[], word_count=4)
    monkeypatch.setattr(process, "ContentProcessor", Processor)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers={"X-API-Key": "regression-key"}) as session:
            pending = asyncio.create_task(session.post("/api/process/", json={"transcript_text": "测试原文", "template": "v9"}))
            while not started.is_set():
                await asyncio.sleep(0.005)
            health = await session.get("/api/health/")
            assert health.status_code == 200
            assert not pending.done(), "Health was delayed until model processing finished"
            result = await pending
            assert result.status_code == 200
            await session.delete(f"/api/notes/{result.json()['saved_note_id']}")
    asyncio.run(run())


def test_saved_note_image_generation_keeps_body_text(tmp_path, monkeypatch):
    async def render(self, html, destination):
        destination.write_text(html, encoding="utf-8")
    monkeypatch.setattr(ImageGenerator, "_html_to_image", render)
    paths = asyncio.run(ImageGenerator(tmp_path).generate_note_images(
        structured_content={"hook_title": "测试标题", "thinking": "第一段完整正文\n第二段完整正文"},
        source_info={},
    ))
    assert len(paths) == 3
    content = paths[1].read_text(encoding="utf-8")
    assert "第一段完整正文" in content
    assert "第二段完整正文" in content
