"""Settings router for user-configurable application settings."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config.download_settings import (
    DownloadSettingsModel,
    download_settings_manager,
)
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


class DownloadPathRequest(BaseModel):
    """Update download path request."""

    path: str


class DownloadPathResponse(BaseModel):
    """Download path response."""

    current_path: str
    is_custom: bool
    default_path: str


class PathValidationResponse(BaseModel):
    """Path validation response."""

    valid: bool
    path: str
    writable: bool
    error: str | None = None


@router.get("/download-path", response_model=DownloadPathResponse)
async def get_download_path():
    """获取当前下载路径设置."""
    settings = download_settings_manager.load()
    effective = settings.get_effective_download_dir()

    return DownloadPathResponse(
        current_path=str(effective),
        is_custom=settings.custom_download_dir is not None,
        default_path=str(effective) if not settings.custom_download_dir else "",
    )


@router.post("/download-path", response_model=DownloadPathResponse)
async def set_download_path(request: DownloadPathRequest):
    """设置自定义下载路径."""
    validation = download_settings_manager.validate_path(request.path)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])

    settings = download_settings_manager.load()
    settings.custom_download_dir = request.path
    download_settings_manager.save(settings)

    effective = settings.get_effective_download_dir()
    return DownloadPathResponse(
        current_path=str(effective),
        is_custom=True,
        default_path="",
    )


@router.post("/download-path/reset", response_model=DownloadPathResponse)
async def reset_download_path():
    """重置为默认下载路径."""
    settings = download_settings_manager.reset()
    effective = settings.get_effective_download_dir()
    return DownloadPathResponse(
        current_path=str(effective),
        is_custom=False,
        default_path=str(effective),
    )


@router.post("/download-path/validate", response_model=PathValidationResponse)
async def validate_download_path(request: DownloadPathRequest):
    """验证下载路径是否可用."""
    result = download_settings_manager.validate_path(request.path)
    return PathValidationResponse(
        valid=result["valid"],
        path=result["path"],
        writable=result["writable"],
        error=result["error"],
    )
