"""后端 API 安全工具 — 统一鉴权与路径白名单 (P0 加固).

提供:
- ApiKeyMiddleware: 基于 PODCAST_NOTES_API_KEY 的统一鉴权中间件
- is_path_allowed:   /transcribe/by-path 等按路径访问接口的目录白名单校验

鉴权策略（默认安全 / fail-closed）:
- 已配置 API Key: 请求必须携带 X-API-Key（或 Authorization: Bearer <key>）且匹配
- 未配置 API Key 且未显式允许匿名: 所有业务接口返回 503，拒绝服务
- 未配置 API Key 且 PODCAST_NOTES_ALLOW_ANONYMOUS=true: 允许匿名（仅建议本地单人使用）
"""

from __future__ import annotations

import hmac
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from config import settings
from utils import get_logger

logger = get_logger(__name__)

# 无需鉴权的路径：根路径、健康检查与 API 文档
PUBLIC_EXACT_PATHS = {"/", "/docs", "/redoc", "/openapi.json"}
PUBLIC_PATH_PREFIXES = ("/api/health", "/images")

API_KEY_HEADER = "X-API-Key"
AUTHORIZATION_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """统一 API Key 鉴权中间件.

    密钥从环境变量 PODCAST_NOTES_API_KEY 读取；
    未配置时默认拒绝所有业务请求（fail-closed），
    可通过 PODCAST_NOTES_ALLOW_ANONYMOUS=true 显式允许匿名。
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._api_key: str = (settings.podcast_notes_api_key or "").strip()
        self._allow_anonymous: bool = settings.podcast_notes_allow_anonymous

        if not self._api_key:
            if self._allow_anonymous:
                logger.warning(
                    "API 鉴权未启用：未配置 PODCAST_NOTES_API_KEY，"
                    "且 PODCAST_NOTES_ALLOW_ANONYMOUS=true 已显式允许匿名访问（仅建议本地单人使用）"
                )
            else:
                logger.warning(
                    "API 鉴权未配置：请设置环境变量 PODCAST_NOTES_API_KEY；"
                    "在配置之前，所有业务接口将返回 503 拒绝访问"
                )

    def _is_public_path(self, path: str) -> bool:
        return path in PUBLIC_EXACT_PATHS or path.startswith(PUBLIC_PATH_PREFIXES)

    def _extract_provided_key(self, request: Request) -> str | None:
        provided = request.headers.get(API_KEY_HEADER)
        if provided:
            return provided.strip()

        authorization = request.headers.get(AUTHORIZATION_HEADER)
        if authorization and authorization.startswith(BEARER_PREFIX):
            return authorization[len(BEARER_PREFIX):].strip()

        return None

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if self._is_public_path(request.url.path):
            return await call_next(request)

        if not self._api_key:
            if self._allow_anonymous:
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "API 鉴权未配置：请在服务端设置环境变量 PODCAST_NOTES_API_KEY。"
                        "如确需本地匿名访问，可显式设置 PODCAST_NOTES_ALLOW_ANONYMOUS=true。"
                    )
                },
            )

        provided = self._extract_provided_key(request)
        if provided is None or not hmac.compare_digest(provided, self._api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "无效或缺失的 API Key（X-API-Key）"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        return await call_next(request)


def get_allowed_audio_roots() -> list[Path]:
    """获取允许 /transcribe/by-path 访问的根目录列表（绝对路径、已 resolve）.

    包含 settings 中的音频下载目录、上传/输出目录与临时目录，
    以及用户在下载设置中自定义的下载目录。
    """
    roots: list[Path] = []

    for candidate in (settings.audio_download_dir, settings.output_dir, settings.temp_dir):
        roots.append(candidate)

    try:
        from backend.config.download_settings import download_settings_manager

        roots.append(download_settings_manager.load().get_effective_download_dir())
    except Exception as e:  # noqa: BLE001 - 自定义目录读取失败时忽略，不影响基础白名单
        logger.warning("读取自定义下载目录失败，跳过该白名单根目录", error=str(e))

    return [root.resolve() for root in roots]


def is_path_allowed(file_path: Path) -> bool:
    """校验路径是否位于允许的根目录内（resolve 后前缀校验，拒绝目录穿越）."""
    try:
        resolved = file_path.resolve()
    except (OSError, RuntimeError):
        return False

    for root in get_allowed_audio_roots():
        if resolved == root or resolved.is_relative_to(root):
            return True
    return False


__all__ = ["ApiKeyMiddleware", "get_allowed_audio_roots", "is_path_allowed"]