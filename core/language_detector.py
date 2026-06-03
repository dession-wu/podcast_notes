"""语言检测模块 — 多层级播客音频语言检测.

支持基于 RSS 元数据、文件名模式、音频采样的多层级检测策略，
为 STT 智能路由提供语言信息。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from models.podcast import PodcastEpisode
from utils import get_logger

logger = get_logger(__name__)


class LanguageDetectorError(Exception):
    """语言检测错误."""

    pass


class LanguageDetector:
    """多层级语言检测器.

    检测策略优先级：
    1. RSS 元数据 (<language> 标签)
    2. 播客标题/描述中的语言线索
    3. 文件名模式匹配
    4. 音频内容采样检测 (兜底)
    """

    # 语言代码标准化映射
    LANG_MAP = {
        # 中文
        "zh": "zh",
        "zh-cn": "zh",
        "zh-tw": "zh",
        "zh-hk": "zh",
        "cmn": "zh",
        # 粤语
        "yue": "yue",
        "zh-yue": "yue",
        "cantonese": "yue",
        # 英文
        "en": "en",
        "en-us": "en",
        "en-gb": "en",
        "english": "en",
        # 日语
        "ja": "ja",
        "jp": "ja",
        "japanese": "ja",
        # 韩语
        "ko": "ko",
        "kr": "ko",
        "korean": "ko",
    }

    # 文件名模式匹配规则
    FILENAME_PATTERNS = [
        (r"[\u4e00-\u9fff]{3,}", "zh"),           # 包含3个以上中文字符
        (r"\b(cn|chinese|中文|国语|普通话)\b", "zh"),
        (r"\b(yue|cantonese|粤语|广东话)\b", "yue"),
        (r"\b(jp|japanese|日语|日文)\b", "ja"),
        (r"\b(kr|korean|韩语|韩文|朝鲜语)\b", "ko"),
        (r"\b(en|english|英文|英语)\b", "en"),
    ]

    # 语言到 STT 引擎的映射
    # 注意：所有语言默认路由到 SenseVoice，因为它支持多语言且已安装
    # Whisper/faster-whisper 作为可选引擎，需要手动指定
    ENGINE_MAP = {
        "zh": "sensevoice",
        "yue": "sensevoice",
        "ja": "sensevoice",
        "ko": "sensevoice",
        "en": "sensevoice",  # Changed from "whisper" to "sensevoice" for reliability
    }

    def __init__(self, sample_seconds: int = 15) -> None:
        """初始化语言检测器.

        Args:
            sample_seconds: 音频采样检测时长(秒)
        """
        self.sample_seconds = sample_seconds

    def detect(self, episode: PodcastEpisode) -> dict[str, Any]:
        """检测播客音频语言.

        按优先级依次尝试不同检测策略，返回最可靠的结果。

        Args:
            episode: 播客单集对象

        Returns:
            {
                "language": "zh/en/yue/ja/ko/unknown",
                "confidence": "high/medium/low",
                "method": "rss/title/filename/audio",
                "engine": "sensevoice/whisper",
            }
        """
        # 策略 1: RSS 元数据
        result = self._detect_from_rss(episode)
        if result:
            logger.info("语言检测: RSS元数据", language=result["language"])
            return result

        # 策略 2: 标题和描述
        result = self._detect_from_text(episode)
        if result:
            logger.info("语言检测: 标题/描述", language=result["language"])
            return result

        # 策略 3: 文件名
        result = self._detect_from_filename(episode)
        if result:
            logger.info("语言检测: 文件名", language=result["language"])
            return result

        # 策略 4: 音频采样 (兜底)
        result = self._detect_from_audio(episode)
        if result:
            logger.info("语言检测: 音频采样", language=result["language"])
            return result

        # 无法检测，默认使用 SenseVoice（支持多语言）
        logger.warning("语言检测失败，默认使用 SenseVoice", episode=episode.title)
        return {
            "language": "unknown",
            "confidence": "low",
            "method": "default",
            "engine": "sensevoice",  # Default to SenseVoice for reliability
        }

    def _detect_from_rss(self, episode: PodcastEpisode) -> dict[str, Any] | None:
        """从 RSS 元数据检测语言."""
        # 尝试从 feed 语言检测
        if hasattr(episode, "feed_language") and episode.feed_language:
            lang = self._normalize_lang(episode.feed_language)
            if lang:
                return {
                    "language": lang,
                    "confidence": "high",
                    "method": "rss",
                    "engine": self.ENGINE_MAP.get(lang, "whisper"),
                }
        return None

    def _detect_from_text(self, episode: PodcastEpisode) -> dict[str, Any] | None:
        """从播客标题和描述检测语言."""
        text = ""
        if episode.title:
            text += episode.title + " "
        if hasattr(episode, "description") and episode.description:
            text += episode.description

        if not text:
            return None

        # 检测中文字符比例
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.strip())

        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return {
                "language": "zh",
                "confidence": "medium",
                "method": "title",
                "engine": "sensevoice",
            }

        # 检测日文假名
        japanese_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", text))
        if total_chars > 0 and japanese_chars / total_chars > 0.3:
            return {
                "language": "ja",
                "confidence": "medium",
                "method": "title",
                "engine": "sensevoice",
            }

        # 检测韩文
        korean_chars = len(re.findall(r"[\uac00-\ud7af]", text))
        if total_chars > 0 and korean_chars / total_chars > 0.3:
            return {
                "language": "ko",
                "confidence": "medium",
                "method": "title",
                "engine": "sensevoice",
            }

        # 如果主要是 ASCII 字符，推测为英文
        ascii_chars = len(re.findall(r"[a-zA-Z]", text))
        if total_chars > 0 and ascii_chars / total_chars > 0.5:
            return {
                "language": "en",
                "confidence": "medium",
                "method": "title",
                "engine": "sensevoice",  # Route to SenseVoice for reliability
            }

        return None

    def _detect_from_filename(self, episode: PodcastEpisode) -> dict[str, Any] | None:
        """从文件名检测语言."""
        if not episode.local_audio_path:
            return None

        filename = episode.local_audio_path.name.lower()

        for pattern, lang in self.FILENAME_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return {
                    "language": lang,
                    "confidence": "medium",
                    "method": "filename",
                    "engine": self.ENGINE_MAP.get(lang, "whisper"),
                }

        return None

    def _detect_from_audio(self, episode: PodcastEpisode) -> dict[str, Any] | None:
        """从音频内容采样检测语言 (兜底策略).

        使用轻量级的音频语言识别方法。
        """
        if not episode.local_audio_path:
            return None

        audio_path = episode.local_audio_path
        if not audio_path.exists():
            return None

        try:
            # 尝试使用 ffprobe 获取音频语言元数据
            import subprocess

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                import json

                info = json.loads(result.stdout)
                # 检查音频流中的语言标签
                for stream in info.get("streams", []):
                    lang = stream.get("tags", {}).get("language")
                    if lang:
                        normalized = self._normalize_lang(lang)
                        if normalized:
                            return {
                                "language": normalized,
                                "confidence": "medium",
                                "method": "audio_metadata",
                                "engine": self.ENGINE_MAP.get(normalized, "whisper"),
                            }

        except Exception as e:
            logger.debug("音频元数据检测失败", error=str(e))

        # 如果以上都失败，尝试快速转录样本检测
        # 注意：这里使用一个简化的方法，实际生产环境可以使用更轻量的模型
        return None

    def _normalize_lang(self, lang_code: str) -> str | None:
        """标准化语言代码."""
        if not lang_code:
            return None

        normalized = lang_code.lower().strip()
        return self.LANG_MAP.get(normalized)

    def get_engine_for_language(self, language: str) -> str:
        """根据语言获取推荐的 STT 引擎.

        Args:
            language: 语言代码

        Returns:
            推荐的引擎名称 (sensevoice/whisper)
        """
        return self.ENGINE_MAP.get(language, "whisper")
