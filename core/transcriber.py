"""语音转文字模块 — 支持多种 STT 引擎.

支持引擎：
- Whisper (OpenAI 本地版)
- faster-whisper (优化版)
- 预留接口：SenseVoice, ElevenLabs Scribe
- 说话人分离：pyannote.audio（可选）
"""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path
from typing import Any

from config import settings
from config.settings import STTProvider
from models.podcast import PodcastEpisode
from models.transcript import Transcript, TranscriptSegment
from utils import get_logger

logger = get_logger(__name__)


class TranscriberError(Exception):
    """转录相关错误."""

    pass


class Transcriber:
    """语音转文字处理器.

    根据配置自动选择 STT 引擎，将音频文件转换为文本。
    可选支持说话人分离功能。
    """

    def __init__(
        self,
        provider: STTProvider | None = None,
        enable_diarization: bool = False,
        max_speakers: int | None = None,
    ) -> None:
        """初始化转录器.

        Args:
            provider: STT 提供商，默认使用配置中的设置
            enable_diarization: 是否启用说话人分离
            max_speakers: 最大说话人数（None 为自动检测）
        """
        self.provider = provider or settings.stt_provider
        self.output_dir = settings.transcript_dir
        self.enable_diarization = enable_diarization or getattr(
            settings, "enable_speaker_diarization", False
        )
        self.max_speakers = max_speakers or getattr(settings, "max_speakers", None)

        # 引擎实例（延迟加载）
        self._whisper_model = None
        self._faster_whisper_model = None
        self._sensevoice_model = None
        self._diarizer = None

        logger.info(
            "转录器初始化完成",
            provider=self.provider.value,
            diarization=self.enable_diarization,
        )

    def transcribe(
        self,
        episode: PodcastEpisode,
        language: str | None = "zh",
    ) -> Transcript:
        """转录音频文件.

        Args:
            episode: 播客单集对象（需包含 local_audio_path）
            language: 音频语言，默认中文

        Returns:
            转录文本对象

        Raises:
            TranscriberError: 转录失败
        """
        if not episode.local_audio_path:
            raise TranscriberError("播客单集缺少本地音频路径")

        audio_path = episode.local_audio_path

        if not audio_path.exists():
            raise TranscriberError(f"音频文件不存在: {audio_path}")

        logger.info(
            "开始语音转文字",
            episode=episode.title,
            provider=self.provider.value,
            language=language,
        )

        # 根据提供商选择转录方法
        match self.provider:
            case STTProvider.WHISPER:
                transcript = self._transcribe_with_whisper(audio_path, language)
            case STTProvider.FASTER_WHISPER:
                transcript = self._transcribe_with_faster_whisper(audio_path, language)
            case STTProvider.SENSEVOICE:
                transcript = self._transcribe_with_sensevoice(audio_path, language)
            case STTProvider.ELEVENLABS:
                transcript = self._transcribe_with_elevenlabs(audio_path, language)
            case _:
                raise TranscriberError(f"不支持的 STT 提供商: {self.provider}")

        # 如果启用了说话人分离但转录结果中没有说话人信息，
        # 使用 pyannote 进行独立说话人分离并对齐
        if self.enable_diarization and not any(s.speaker for s in transcript.segments):
            logger.info("应用独立说话人分离对齐")
            transcript = self._apply_independent_diarization_with_path(
                transcript, audio_path
            )

        # 补充元数据（确保所有解析器都能正确传递）
        transcript.episode_title = episode.title
        transcript.podcast_name = episode.feed_title or episode.get_podcast_name_from_title()
        transcript.audio_path = audio_path
        transcript.stt_provider = self.provider.value
        transcript.diarization_enabled = self.enable_diarization

        # 保存转录文本
        self._save_transcript(transcript)

        logger.info(
            "语音转文字完成",
            episode=episode.title,
            word_count=transcript.word_count,
            segments=transcript.segment_count,
        )

        return transcript

    def _transcribe_with_whisper(
        self,
        audio_path: Path,
        language: str | None,
    ) -> Transcript:
        """使用 OpenAI Whisper 本地转录.

        Args:
            audio_path: 音频文件路径
            language: 音频语言

        Returns:
            转录文本对象
        """
        try:
            import whisper
        except ImportError:
            raise TranscriberError(
                "未安装 openai-whisper，请运行: pip install openai-whisper"
            )

        # 延迟加载模型
        if self._whisper_model is None:
            model_name = settings.whisper_model
            logger.info("正在加载 Whisper 模型", model=model_name)
            self._whisper_model = whisper.load_model(model_name)

        # 执行转录
        result = self._whisper_model.transcribe(
            str(audio_path),
            language=language,
            verbose=False,
        )

        return self._parse_whisper_result(result)

    def _transcribe_with_faster_whisper(
        self,
        audio_path: Path,
        language: str | None,
    ) -> Transcript:
        """使用 faster-whisper 转录.

        faster-whisper 比标准 Whisper 快 3-5 倍，支持量化加速。
        可选启用说话人分离功能。

        Args:
            audio_path: 音频文件路径
            language: 音频语言

        Returns:
            转录文本对象
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriberError(
                "未安装 faster-whisper，请运行: pip install faster-whisper"
            )

        # 延迟加载模型
        if self._faster_whisper_model is None:
            model_name = settings.faster_whisper_model
            device = settings.faster_whisper_device
            compute_type = settings.faster_whisper_compute_type

            # 自动检测 GPU
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    compute_type = "float16" if device == "cuda" else "int8"
                except ImportError:
                    device = "cpu"
                    compute_type = "int8"

            logger.info(
                "正在加载 faster-whisper 模型",
                model=model_name,
                device=device,
                compute_type=compute_type,
            )
            self._faster_whisper_model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
            )

        # 构建转录参数
        transcribe_params = {
            "language": language,
            "beam_size": 5,
            "vad_filter": True,
        }

        # 如果启用说话人分离，添加相关参数
        if self.enable_diarization:
            transcribe_params["word_timestamps"] = True

            # 尝试使用 faster-whisper 原生 diarization（如果安装了 pyannote）
            try:
                from pyannote.audio import Pipeline  # noqa: F401
                transcribe_params["diarization"] = True
                if self.max_speakers is not None:
                    transcribe_params["max_speakers"] = self.max_speakers
                logger.info("已启用 faster-whisper 原生说话人分离")
            except ImportError:
                logger.warning(
                    "pyannote.audio 未安装，将使用独立说话人分离流程"
                )

        # 执行转录
        segments, info = self._faster_whisper_model.transcribe(
            str(audio_path),
            **transcribe_params,
        )

        return self._parse_faster_whisper_result(segments, info)

    def _transcribe_with_sensevoice(
        self,
        audio_path: Path,
        language: str | None,
    ) -> Transcript:
        """使用 SenseVoice 转录.

        利用阿里开源的 SenseVoice 模型进行语音识别，支持：
        - 多语言识别（中/粤/英/日/韩等）
        - 语音情感识别
        - 音频事件检测
        - VAD 长音频自动切分

        Args:
            audio_path: 音频文件路径
            language: 音频语言（zh/en/yue/ja/ko/auto）

        Returns:
            转录文本对象

        Raises:
            TranscriberError: 转录失败
        """
        try:
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
        except ImportError:
            raise TranscriberError(
                "未安装 funasr，请运行: pip install funasr modelscope"
            )

        # 延迟加载模型
        if self._sensevoice_model is None:
            # 自动检测 GPU
            try:
                import torch
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

            logger.info(
                "正在加载 SenseVoice 模型",
                model="iic/SenseVoiceSmall",
                device=device,
            )
            self._sensevoice_model = AutoModel(
                model="iic/SenseVoiceSmall",
                trust_remote_code=True,
                vad_model="fsmn-vad",
                vad_kwargs={
                    "max_single_segment_time": 30000,
                    "min_single_segment_time": 5000,  # 避免过短片段
                },
                device=device,
            )

        # 语言映射
        lang_map = {"zh": "auto", "en": "auto", "ja": "auto", "ko": "auto"}
        sv_language = lang_map.get(language, "auto") if language else "auto"

        # 执行转录
        logger.info("SenseVoice 开始转录", audio=str(audio_path), language=sv_language)
        res = self._sensevoice_model.generate(
            input=str(audio_path),
            cache={},
            language=sv_language,
            use_itn=True,
            batch_size_s=120,  # 增加批次大小提高吞吐量
            merge_vad=True,
            merge_length_s=15,
        )

        return self._parse_sensevoice_result(res)

    def _parse_sensevoice_result(self, result: list[dict[str, Any]]) -> Transcript:
        """解析 SenseVoice 转录结果.

        SenseVoice 输出格式：
        [{"key": "xxx", "text": "<|zh|><|NEUTRAL|><|Speech|><|withitn|>文本内容", "timestamp": [[0, 3000], ...]}]

        Args:
            result: SenseVoice 返回的结果列表

        Returns:
            转录文本对象
        """
        import re

        segments = []
        full_text_parts = []

        for item in result:
            raw_text = item.get("text", "")
            timestamps = item.get("timestamp", [])

            # 解析 SenseVoice 的特殊 token
            # 格式: <|language|><|emotion|><|event|><|itn|>text
            lang_match = re.search(r"<\|(zh|en|yue|ja|ko|nospeech)\|>", raw_text)
            emotion_match = re.search(r"<\|(NEUTRAL|HAPPY|SAD|ANGRY|EXCITED|EMO_UNKNOWN)\|>", raw_text)
            event_match = re.search(r"<\|(Speech|Applause|Laughter|Crying|Sneeze|Breath|Cough|Music|Noise)\|>", raw_text)
            itn_match = re.search(r"<\|(withitn|woitn)\|>", raw_text)

            # 提取纯文本（移除所有特殊 token）
            clean_text = re.sub(r"<\|[^|]+\|>", "", raw_text).strip()

            # 处理时间戳
            if timestamps and len(timestamps) > 0:
                start_ms = timestamps[0][0] if timestamps[0] else 0
                end_ms = timestamps[-1][1] if timestamps[-1] and len(timestamps[-1]) > 1 else start_ms + 5000
                start_time = start_ms / 1000.0
                end_time = end_ms / 1000.0
            else:
                start_time = 0.0
                end_time = 0.0

            if clean_text:
                segments.append(
                    TranscriptSegment(
                        start_time=start_time,
                        end_time=end_time,
                        text=clean_text,
                        emotion=emotion_match.group(1) if emotion_match else None,
                        audio_event=event_match.group(1) if event_match else None,
                    )
                )
                full_text_parts.append(clean_text)

        full_text = " ".join(full_text_parts)

        # 检测语言
        language = "unknown"
        if segments:
            first_text = result[0].get("text", "") if result else ""
            lang_match = re.search(r"<\|(zh|en|yue|ja|ko)\|>", first_text)
            if lang_match:
                language = lang_match.group(1)

        return Transcript(
            segments=segments,
            full_text=full_text,
            language=language,
            duration_seconds=segments[-1].end_time if segments else None,
            episode_title="",
        )

    def _transcribe_with_elevenlabs(
        self,
        audio_path: Path,
        language: str | None,
    ) -> Transcript:
        """使用 ElevenLabs Scribe API 转录（预留接口）.

        Args:
            audio_path: 音频文件路径
            language: 音频语言

        Returns:
            转录文本对象

        Raises:
            TranscriberError: 当前版本未实现
        """
        if not settings.is_elevenlabs_configured:
            raise TranscriberError(
                "ElevenLabs API 密钥未配置，请在 .env 中设置 ELEVENLABS_API_KEY"
            )

        raise TranscriberError(
            "ElevenLabs Scribe 支持即将推出，当前请使用 whisper 或 faster-whisper"
        )

    def _parse_whisper_result(self, result: dict[str, Any]) -> Transcript:
        """解析 Whisper 转录结果.

        Args:
            result: Whisper 返回的结果字典

        Returns:
            转录文本对象
        """
        segments = []
        for seg in result.get("segments", []):
            segments.append(
                TranscriptSegment(
                    start_time=seg.get("start", 0.0),
                    end_time=seg.get("end", 0.0),
                    text=seg.get("text", "").strip(),
                    confidence=seg.get("avg_logprob", None),
                )
            )

        # 构建完整文本
        full_text = result.get("text", "").strip()

        return Transcript(
            segments=segments,
            full_text=full_text,
            language=result.get("language", "unknown"),
            duration_seconds=segments[-1].end_time if segments else None,
        )

    def _parse_faster_whisper_result(
        self,
        segments: Any,
        info: Any,
    ) -> Transcript:
        """解析 faster-whisper 转录结果.

        Args:
            segments: faster-whisper 返回的片段生成器
            info: 音频信息

        Returns:
            转录文本对象
        """
        transcript_segments = []
        full_text_parts = []

        for seg in segments:
            # 提取说话人信息（如果启用了 diarization）
            speaker = None
            if self.enable_diarization and hasattr(seg, "speaker"):
                speaker = seg.speaker
            elif self.enable_diarization and hasattr(seg, "spk"):
                # faster-whisper 可能使用 spk 字段
                speaker = seg.spk

            transcript_segments.append(
                TranscriptSegment(
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text.strip(),
                    speaker=speaker,
                    confidence=seg.avg_logprob,
                )
            )
            full_text_parts.append(seg.text.strip())

        full_text = " ".join(full_text_parts)

        # 如果启用了说话人分离但 faster-whisper 没有返回说话人信息，
        # 使用 pyannote 进行独立说话人分离并与转录结果对齐
        if self.enable_diarization and not any(
            s.speaker for s in transcript_segments
        ):
            logger.info("faster-whisper 未返回说话人信息，使用 pyannote 独立分离")
            transcript_segments = self._apply_independent_diarization(
                transcript_segments
            )

        return Transcript(
            segments=transcript_segments,
            full_text=full_text,
            language=info.language if info else "unknown",
            duration_seconds=transcript_segments[-1].end_time if transcript_segments else None,
        )

    def _apply_independent_diarization(
        self,
        transcript_segments: list[TranscriptSegment],
    ) -> list[TranscriptSegment]:
        """使用 pyannote 独立进行说话人分离并对齐到转录结果.

        当 STT 引擎不支持原生 diarization 时的回退方案。

        Args:
            transcript_segments: 转录片段列表

        Returns:
            带说话人标签的转录片段列表
        """
        try:
            from core.speaker_diarizer import AlignmentEngine, SpeakerDiarizer

            # 延迟加载说话人分离器
            if self._diarizer is None:
                hf_token = getattr(settings, "hf_token", None)
                self._diarizer = SpeakerDiarizer(
                    max_speakers=self.max_speakers,
                    hf_token=hf_token,
                )

            # 注意：这里需要音频路径来执行说话人分离
            # 但 _parse_faster_whisper_result 没有访问音频路径的能力
            # 所以这个独立分离应该在更高层调用
            logger.warning(
                "独立说话人分离需要音频路径，请在 transcribe() 方法中调用"
            )
            return transcript_segments

        except ImportError:
            logger.warning("pyannote.audio 未安装，跳过独立说话人分离")
            return transcript_segments
        except Exception as e:
            logger.warning(f"独立说话人分离失败: {e}")
            return transcript_segments

    def _apply_independent_diarization_with_path(
        self,
        transcript: Transcript,
        audio_path: Path,
    ) -> Transcript:
        """使用 pyannote 独立进行说话人分离并对齐到转录结果（带音频路径）.

        Args:
            transcript: 转录文本对象
            audio_path: 音频文件路径

        Returns:
            带说话人标签的转录文本对象
        """
        try:
            from core.speaker_diarizer import SpeakerDiarizer

            # 延迟加载说话人分离器
            if self._diarizer is None:
                hf_token = getattr(settings, "hf_token", None)
                self._diarizer = SpeakerDiarizer(
                    max_speakers=self.max_speakers,
                    hf_token=hf_token,
                )

            # 执行说话人分离
            diarization = self._diarizer.diarize(audio_path)

            # 对齐说话人标签到转录片段
            aligned_segments = []
            for seg in transcript.segments:
                speaker = self._diarizer._find_best_matching_speaker(seg, diarization)
                aligned_segments.append(
                    TranscriptSegment(
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        text=seg.text,
                        speaker=speaker,
                        confidence=seg.confidence,
                        emotion=seg.emotion,
                        audio_event=seg.audio_event,
                    )
                )

            # 更新转录对象
            transcript.segments = aligned_segments
            transcript.diarization_enabled = True
            transcript.speaker_count = diarization.speaker_count

            # 保存说话人分离结果
            diag_output_dir = settings.transcript_dir / "diarization"
            safe_title = "".join(
                c for c in transcript.episode_title if c.isalnum() or c in (" ", "-", "_")
            ).strip()[:50]
            diag_path = diag_output_dir / f"{safe_title}_diarization.json"
            diarization.save_to_file(diag_path)
            transcript.diarization_result_path = str(diag_path)

            logger.info(
                "独立说话人分离完成",
                speakers=diarization.speaker_count,
                segments=len(aligned_segments),
            )

            return transcript

        except ImportError:
            logger.warning("pyannote.audio 未安装，跳过独立说话人分离")
            transcript.diarization_enabled = False
            return transcript
        except Exception as e:
            logger.warning(f"独立说话人分离失败: {e}")
            transcript.diarization_enabled = False
            return transcript

    def _save_transcript(self, transcript: Transcript) -> None:
        """保存转录文本到文件.

        Args:
            transcript: 转录文本对象
        """
        safe_title = "".join(
            c for c in transcript.episode_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:50]

        output_path = self.output_dir / f"{safe_title}_transcript.md"
        transcript.save_to_file(output_path)

        logger.info("转录文本已保存", path=str(output_path))

    def check_audio_file(self, audio_path: Path) -> dict[str, Any]:
        """检查音频文件信息.

        Args:
            audio_path: 音频文件路径

        Returns:
            音频文件信息字典
        """
        if not audio_path.exists():
            return {"exists": False, "error": "文件不存在"}

        # 使用 ffprobe 获取音频信息
        try:
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
                check=True,
                encoding="utf-8",
                errors="replace",
            )
            import json
            if result.stdout:
                info = json.loads(result.stdout)
            else:
                raise subprocess.CalledProcessError(
                    result.returncode, result.args, output=result.stdout, stderr=result.stderr
                )

            format_info = info.get("format", {})
            duration = float(format_info.get("duration", 0))
            size = int(format_info.get("size", 0))
            bitrate = int(format_info.get("bit_rate", 0))

            return {
                "exists": True,
                "duration_seconds": duration,
                "duration_formatted": self._format_duration(duration),
                "size_mb": round(size / 1024 / 1024, 2),
                "bitrate_kbps": round(bitrate / 1000, 0),
                "format": format_info.get("format_name", "unknown"),
            }
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"ffprobe 获取音频信息失败: {e}")
            # ffprobe 不可用或输出解析失败，返回基本信息
            size = audio_path.stat().st_size
            return {
                "exists": True,
                "size_mb": round(size / 1024 / 1024, 2),
                "duration_seconds": None,
                "note": "ffprobe 不可用，无法获取时长信息",
            }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化秒数为可读字符串.

        Args:
            seconds: 秒数

        Returns:
            格式化后的字符串，如 "1:23:45"
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
