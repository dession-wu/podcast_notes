"""智能转录器 — 基于语言自动路由到最优 STT 引擎.

整合 LanguageDetector、SenseVoice、Whisper，根据音频语言自动选择最优引擎，
提供统一的转录接口。
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from config import settings
from core.language_detector import LanguageDetector
from core.transcriber import (
    STTProvider,
    Transcriber,
    TranscriberError,
    Transcript,
)
from models.podcast import PodcastEpisode
from utils import get_logger

logger = get_logger(__name__)


class SmartTranscriberError(Exception):
    """智能转录器错误."""

    pass


class SmartTranscriber:
    """智能转录器.

    根据音频语言自动选择最优 STT 引擎：
    - 中文/粤语/日语/韩语 → SenseVoice
    - 英文/其他语言 → Whisper

    支持手动覆盖和自动检测两种模式。
    可选支持说话人分离功能。
    """

    def __init__(
        self,
        enable_diarization: bool = False,
        max_speakers: int | None = None,
    ) -> None:
        """初始化智能转录器.

        Args:
            enable_diarization: 是否启用说话人分离
            max_speakers: 最大说话人数（None 为自动检测）
        """
        self.language_detector = LanguageDetector(
            sample_seconds=getattr(settings, "language_detection_sample_seconds", 15)
        )
        self.enable_diarization = enable_diarization or getattr(
            settings, "enable_speaker_diarization", False
        )
        self.max_speakers = max_speakers or getattr(settings, "max_speakers", None)
        self._whisper_transcriber: Transcriber | None = None
        self._sensevoice_transcriber: Transcriber | None = None
        self._diarization_enabled_for_engine: str = ""

    def _get_whisper_transcriber(self) -> Transcriber:
        """获取 Whisper 转录器实例 (延迟加载).

        优先使用 faster-whisper（如果可用），否则回退到标准 Whisper。
        如果启用了说话人分离，将参数传递给转录器。
        """
        if self._whisper_transcriber is None:
            # 尝试使用 faster-whisper，如果未安装则回退到标准 Whisper
            try:
                from faster_whisper import WhisperModel  # noqa: F401
                logger.info("初始化 faster-whisper 转录器")
                self._whisper_transcriber = Transcriber(
                    provider=STTProvider.FASTER_WHISPER,
                    enable_diarization=self.enable_diarization,
                    max_speakers=self.max_speakers,
                )
            except ImportError:
                logger.info("faster-whisper 未安装，使用标准 Whisper")
                self._whisper_transcriber = Transcriber(
                    provider=STTProvider.WHISPER,
                    enable_diarization=self.enable_diarization,
                    max_speakers=self.max_speakers,
                )
        return self._whisper_transcriber

    def _get_sensevoice_transcriber(self) -> Transcriber:
        """获取 SenseVoice 转录器实例 (延迟加载).

        SenseVoice 不支持原生 diarization，将使用独立说话人分离流程。
        """
        if self._sensevoice_transcriber is None:
            logger.info("初始化 SenseVoice 转录器")
            self._sensevoice_transcriber = Transcriber(
                provider=STTProvider.SENSEVOICE,
                enable_diarization=self.enable_diarization,
                max_speakers=self.max_speakers,
            )
        return self._sensevoice_transcriber

    def transcribe(
        self,
        episode: PodcastEpisode,
        force_engine: str | None = None,
    ) -> Transcript:
        """智能转录音频.

        自动检测语言并选择最优引擎，或强制使用指定引擎。

        Args:
            episode: 播客单集对象
            force_engine: 强制指定引擎 ("whisper"/"sensevoice")，None 则自动选择

        Returns:
            转录结果

        Raises:
            SmartTranscriberError: 转录失败
        """
        start_time = time.time()

        # 确定使用的引擎
        if force_engine:
            engine = force_engine
            detection_result = {
                "language": "unknown",
                "confidence": "low",
                "method": "manual",
                "engine": force_engine,
            }
            logger.info("强制使用引擎", engine=engine)
        else:
            # 自动检测语言并选择引擎
            detection_result = self.language_detector.detect(episode)
            engine = detection_result["engine"]
            logger.info(
                "自动选择引擎",
                engine=engine,
                language=detection_result["language"],
                confidence=detection_result["confidence"],
                method=detection_result["method"],
            )

        # 执行转录
        try:
            if engine == "sensevoice":
                transcript = self._transcribe_with_sensevoice(episode)
            else:
                transcript = self._transcribe_with_whisper(episode)

            # 记录转录元数据到 stt_provider 字段
            transcript.stt_provider = engine

            logger.info(
                "智能转录完成",
                engine=engine,
                language=detection_result["language"],
                duration=round(time.time() - start_time, 2),
                word_count=transcript.word_count,
                diarization_enabled=transcript.diarization_enabled,
                speaker_count=transcript.speaker_count,
            )

            return transcript

        except Exception as e:
            logger.error(
                "智能转录失败",
                engine=engine,
                error=str(e),
                episode=episode.title,
            )
            raise SmartTranscriberError(f"转录失败 ({engine}): {e}") from e

    def _transcribe_with_whisper(self, episode: PodcastEpisode) -> Transcript:
        """使用 Whisper 转录，失败时自动回退到 SenseVoice."""
        try:
            transcriber = self._get_whisper_transcriber()
            return transcriber.transcribe(episode)
        except Exception as e:
            logger.warning(
                "Whisper 转录失败，自动回退到 SenseVoice",
                error=str(e),
                episode=episode.title,
            )
            return self._transcribe_with_sensevoice(episode)

    def _transcribe_with_sensevoice(self, episode: PodcastEpisode) -> Transcript:
        """使用 SenseVoice 转录."""
        transcriber = self._get_sensevoice_transcriber()
        return transcriber.transcribe(episode)

    def detect_language_only(self, episode: PodcastEpisode) -> dict[str, Any]:
        """仅检测语言，不执行转录.

        Args:
            episode: 播客单集对象

        Returns:
            语言检测结果
        """
        return self.language_detector.detect(episode)

    @staticmethod
    def get_supported_engines() -> list[dict[str, str]]:
        """获取支持的引擎列表.

        Returns:
            引擎信息列表
        """
        return [
            {
                "id": "whisper",
                "name": "OpenAI Whisper",
                "description": "英文优化，支持99种语言",
                "best_for": "英文、多语言混合",
                "languages": "en, es, fr, de, ... (99种)",
            },
            {
                "id": "sensevoice",
                "name": "阿里 SenseVoice",
                "description": "中文优化，支持情感识别",
                "best_for": "中文、粤语、日语、韩语",
                "languages": "zh, yue, ja, ko",
            },
        ]

    @staticmethod
    def compare_engines() -> dict[str, Any]:
        """获取引擎对比信息.

        Returns:
            对比数据
        """
        return {
            "accuracy": {
                "chinese_cer": {"sensevoice": "4.8%", "whisper": "5.3%"},
                "english_wer": {"sensevoice": "5.2%", "whisper": "4.9%"},
                "accent_chinese": {"sensevoice": "11.3%", "whisper": "18.7%"},
            },
            "speed": {
                "sensevoice": "~70ms/10s音频",
                "whisper": "~350ms/10s音频",
            },
            "features": {
                "sensevoice": ["情感识别", "音频事件检测", "非自回归架构"],
                "whisper": ["99种语言", "自回归架构", "成熟生态"],
            },
        }
