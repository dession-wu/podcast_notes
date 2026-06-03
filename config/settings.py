"""应用配置管理 — 基于 Pydantic Settings 的类型化配置.

使用环境变量和 .env 文件管理所有配置，支持多环境切换。
"""

from __future__ import annotations

import sys
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """支持的 LLM 提供商."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class STTProvider(str, Enum):
    """支持的语音转文字提供商."""

    WHISPER = "whisper"
    FASTER_WHISPER = "faster-whisper"
    SENSEVOICE = "sensevoice"
    ELEVENLABS = "elevenlabs"


class PublishMode(str, Enum):
    """小红书发布模式."""

    RPA = "rpa"
    SEMI_AUTO = "semi-auto"
    MANUAL = "manual"


class Settings(BaseSettings):
    """应用配置类.

    所有配置项通过环境变量或 .env 文件加载，支持类型验证和默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # LLM 配置
    # -------------------------------------------------------------------------
    default_llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="默认 LLM 提供商",
    )

    # OpenAI
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API 密钥",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API 基础 URL",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI 默认模型",
    )

    # Anthropic
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API 密钥",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic 默认模型",
    )

    # Ollama
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama 服务地址",
    )
    ollama_model: str = Field(
        default="qwen2.5:14b",
        description="Ollama 默认模型",
    )

    # -------------------------------------------------------------------------
    # STT 配置
    # -------------------------------------------------------------------------
    stt_provider: STTProvider = Field(
        default=STTProvider.WHISPER,
        description="语音转文字提供商",
    )

    # Whisper
    whisper_model: str = Field(
        default="medium",
        description="Whisper 模型名称 (tiny/base/small/medium/large)",
    )
    whisper_device: Literal["cpu", "cuda", "auto"] = Field(
        default="auto",
        description="Whisper 运行设备 (auto 自动检测 GPU)",
    )
    whisper_compute_type: Literal["int8", "int16", "float16", "float32"] = Field(
        default="int8",
        description="Whisper 计算精度",
    )

    # faster-whisper
    faster_whisper_model: str = Field(
        default="medium",
        description="faster-whisper 模型名称",
    )
    faster_whisper_device: Literal["cpu", "cuda", "auto"] = Field(
        default="auto",
        description="faster-whisper 运行设备 (auto 自动检测 GPU)",
    )
    faster_whisper_compute_type: Literal["int8", "int8_float16", "float16", "float32"] = Field(
        default="int8",
        description="faster-whisper 计算精度 (int8 最快，float16 精度更高)",
    )

    # ElevenLabs
    elevenlabs_api_key: str | None = Field(
        default=None,
        description="ElevenLabs API 密钥",
    )

    # -------------------------------------------------------------------------
    # 说话人分离配置
    # -------------------------------------------------------------------------
    enable_speaker_diarization: bool = Field(
        default=False,
        description="是否启用说话人分离功能",
    )

    diarization_model: str = Field(
        default="pyannote/speaker-diarization-3.1",
        description="说话人分离模型名称",
    )

    max_speakers: int | None = Field(
        default=None,
        description="最大说话人数（None 为自动检测）",
    )

    hf_token: str | None = Field(
        default=None,
        description="HuggingFace API Token（用于下载 pyannote 模型）",
    )

    @property
    def is_diarization_configured(self) -> bool:
        """检查说话人分离是否已配置."""
        return self.enable_speaker_diarization and self.hf_token is not None

    # -------------------------------------------------------------------------
    # 小红书发布配置
    # -------------------------------------------------------------------------
    xiaohongshu_publish_mode: PublishMode = Field(
        default=PublishMode.MANUAL,
        description="小红书发布模式",
    )
    xiaohongshu_rpa_enabled: bool = Field(
        default=False,
        description="是否启用 RPA 自动发布",
    )
    xiaohongshu_chrome_profile: str | None = Field(
        default=None,
        description="Chrome Profile 路径（用于保持登录态）",
    )
    xiaohongshu_headless: bool = Field(
        default=False,
        description="是否使用无头浏览器模式",
    )

    # -------------------------------------------------------------------------
    # 播客搜索配置
    # -------------------------------------------------------------------------
    podcastindex_api_key: str | None = Field(
        default=None,
        description="PodcastIndex API Key",
    )
    podcastindex_api_secret: str | None = Field(
        default=None,
        description="PodcastIndex API Secret",
    )
    listennotes_api_key: str | None = Field(
        default=None,
        description="ListenNotes API Key (备用源)",
    )

    @property
    def is_podcastindex_configured(self) -> bool:
        """检查 PodcastIndex 是否已配置."""
        return (
            self.podcastindex_api_key is not None
            and len(self.podcastindex_api_key) > 0
            and self.podcastindex_api_secret is not None
            and len(self.podcastindex_api_secret) > 0
        )

    @property
    def is_listennotes_configured(self) -> bool:
        """检查 ListenNotes 是否已配置."""
        return self.listennotes_api_key is not None and len(self.listennotes_api_key) > 0

    # -------------------------------------------------------------------------
    # 系统配置
    # -------------------------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        description="日志级别",
    )
    data_dir: Path = Field(
        default=Path("./data"),
        description="数据存储目录",
    )
    temp_dir: Path = Field(
        default=Path("./data/temp"),
        description="临时文件目录",
    )
    request_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="HTTP 请求超时时间（秒）",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数",
    )

    # -------------------------------------------------------------------------
    # 验证器
    # -------------------------------------------------------------------------
    @field_validator("data_dir", "temp_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """确保路径为 Path 对象并创建目录."""
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path

    @field_validator("temp_dir", mode="after")
    @classmethod
    def ensure_temp_subdir(cls, v: Path) -> Path:
        """确保临时目录存在."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    # -------------------------------------------------------------------------
    # 便捷属性
    # -------------------------------------------------------------------------
    @property
    def is_openai_configured(self) -> bool:
        """检查 OpenAI 是否已配置."""
        return self.openai_api_key is not None and len(self.openai_api_key) > 0

    @property
    def is_anthropic_configured(self) -> bool:
        """检查 Anthropic 是否已配置."""
        return self.anthropic_api_key is not None and len(self.anthropic_api_key) > 0

    @property
    def is_elevenlabs_configured(self) -> bool:
        """检查 ElevenLabs 是否已配置."""
        return self.elevenlabs_api_key is not None and len(self.elevenlabs_api_key) > 0

    @property
    def audio_download_dir(self) -> Path:
        """音频下载目录."""
        path = self.data_dir / "audio"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def transcript_dir(self) -> Path:
        """转录文本存储目录."""
        path = self.data_dir / "transcripts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_dir(self) -> Path:
        """输出文件目录."""
        path = self.data_dir / "output"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置单例.

    使用 lru_cache 确保配置只加载一次，提高性能。
    """
    try:
        return Settings()
    except Exception as e:
        print(f"配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)


# 全局配置实例
settings = get_settings()
