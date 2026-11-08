"""Download settings persistence — runtime reloadable path configuration."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from config.settings import settings as app_settings

DEFAULT_CONFIG_PATH = app_settings.data_dir / "config" / "download_config.json"


class DownloadSettingsModel(BaseModel):
    """用户可配置的下载设置."""

    custom_download_dir: str | None = Field(
        default=None,
        description="用户自定义下载目录，None 表示使用默认",
    )

    @field_validator("custom_download_dir")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        """验证路径有效性."""
        if v is None:
            return None
        path = Path(v)
        if path.exists() and not path.is_dir():
            raise ValueError("路径必须是目录")
        return str(path.resolve())

    def get_effective_download_dir(self) -> Path:
        """获取实际生效的下载目录."""
        if self.custom_download_dir:
            path = Path(self.custom_download_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return app_settings.audio_download_dir


class DownloadSettingsManager:
    """下载设置管理器 — 负责读写 JSON 配置文件."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._settings: DownloadSettingsModel | None = None

    def _ensure_config_dir(self) -> None:
        """确保配置文件目录存在."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> DownloadSettingsModel:
        """从 JSON 文件加载设置."""
        if self._settings is not None:
            return self._settings

        source = self.config_path
        legacy = Path("./config/download_config.json")
        if self.config_path == DEFAULT_CONFIG_PATH and not source.exists() and legacy.exists():
            source = legacy
        if source.exists():
            try:
                with open(source, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._settings = DownloadSettingsModel(**data)
            except (json.JSONDecodeError, ValueError):
                self._settings = DownloadSettingsModel()
        else:
            self._settings = DownloadSettingsModel()

        return self._settings

    def save(self, settings: DownloadSettingsModel) -> None:
        """保存设置到 JSON 文件."""
        self._ensure_config_dir()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.config_path.parent, delete=False) as f:
                temporary = f.name
                json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
            os.replace(temporary, self.config_path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        self._settings = settings

    def reset(self) -> DownloadSettingsModel:
        """重置为默认设置."""
        default = DownloadSettingsModel()
        self.save(default)
        return default

    def validate_path(self, path: str) -> dict[str, Any]:
        """验证路径是否可用."""
        result = {
            "valid": False,
            "path": path,
            "error": None,
            "writable": False,
        }
        try:
            if not path.strip() or not Path(path).expanduser().is_absolute():
                raise ValueError("请输入服务器上的绝对目录路径")
            p = Path(path).expanduser().resolve()
            result["path"] = str(p)
            p.mkdir(parents=True, exist_ok=True)
            try:
                with tempfile.TemporaryFile(dir=p):
                    pass
                result["writable"] = True
                result["valid"] = True
            except PermissionError:
                result["error"] = "权限不足，无法写入该目录"
            except OSError as e:
                result["error"] = f"目录测试失败: {e}"
        except Exception as e:
            result["error"] = f"路径无效: {e}"
        return result


download_settings_manager = DownloadSettingsManager()
