"""说话人分离模块 — 基于 pyannote.audio 的说话人识别系统.

支持：
- pyannote.audio 说话人分离（推荐）
- speechbrain 说话人嵌入提取
- 说话人标签对齐（与 STT 结果合并）
- 播客场景优化（主持人注册、交叉对话处理）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import settings
from utils import get_logger

logger = get_logger(__name__)


class DiarizerError(Exception):
    """说话人分离相关错误."""

    pass


@dataclass
class SpeakerSegment:
    """说话人片段（带时间边界）."""

    start_time: float
    end_time: float
    speaker_id: str
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        """片段时长（秒）."""
        return self.end_time - self.start_time


@dataclass
class DiarizationResult:
    """说话人分离结果."""

    segments: list[SpeakerSegment] = field(default_factory=list)
    speaker_count: int = 0
    audio_duration: float = 0.0
    model_name: str = "unknown"
    overlap_detected: bool = False

    @property
    def unique_speakers(self) -> list[str]:
        """获取唯一说话人 ID 列表."""
        return sorted({seg.speaker_id for seg in self.segments})

    def get_segments_by_speaker(self, speaker_id: str) -> list[SpeakerSegment]:
        """获取指定说话人的所有片段."""
        return [seg for seg in self.segments if seg.speaker_id == speaker_id]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "speaker_id": seg.speaker_id,
                    "confidence": seg.confidence,
                }
                for seg in self.segments
            ],
            "speaker_count": self.speaker_count,
            "audio_duration": self.audio_duration,
            "model_name": self.model_name,
            "unique_speakers": self.unique_speakers,
        }

    def save_to_file(self, path: Path) -> None:
        """保存结果到 JSON 文件."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("说话人分离结果已保存", path=str(path))


class SpeakerDiarizer:
    """说话人分离器.

    基于 pyannote.audio 实现说话人分离，支持：
    - 自动检测说话人数量
    - 配置最大说话人数
    - 与 STT 转录结果对齐
    """

    def __init__(
        self,
        model_name: str | None = None,
        max_speakers: int | None = None,
        hf_token: str | None = None,
        device: str = "auto",
    ) -> None:
        """初始化说话人分离器.

        Args:
            model_name: 模型名称，默认使用配置中的设置
            max_speakers: 最大说话人数（None 为自动检测）
            hf_token: HuggingFace API Token
            device: 运行设备（auto/cpu/cuda）
        """
        self.model_name = model_name or getattr(
            settings, "diarization_model", "pyannote/speaker-diarization-3.1"
        )
        self.max_speakers = max_speakers or getattr(settings, "max_speakers", None)
        self.hf_token = hf_token or getattr(settings, "hf_token", None)
        self._device = device

        # 延迟加载
        self._pipeline = None
        self._speaker_embeddings = {}

        logger.info(
            "说话人分离器初始化完成",
            model=self.model_name,
            max_speakers=self.max_speakers,
        )

    def diarize(self, audio_path: Path) -> DiarizationResult:
        """对音频进行说话人分离.

        Args:
            audio_path: 音频文件路径

        Returns:
            说话人分离结果

        Raises:
            DiarizerError: 分离失败
        """
        if not audio_path.exists():
            raise DiarizerError(f"音频文件不存在: {audio_path}")

        logger.info("开始说话人分离", audio=str(audio_path))

        try:
            from pyannote.audio import Pipeline

            # 加载模型（延迟加载）
            if self._pipeline is None:
                self._load_pipeline()

            # 配置参数
            params = {}
            if self.max_speakers is not None:
                params["max_speakers"] = self.max_speakers

            # 执行分离
            diarization = self._pipeline(str(audio_path), **params)

            # 解析结果
            segments = []
            speaker_ids = set()

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_ids.add(speaker)
                segments.append(
                    SpeakerSegment(
                        start_time=turn.start,
                        end_time=turn.end,
                        speaker_id=f"SPEAKER_{speaker}",
                        confidence=1.0,
                    )
                )

            # 获取音频时长（通过最后一段的结束时间估算）
            audio_duration = (
                max(seg.end_time for seg in segments) if segments else 0.0
            )

            result = DiarizationResult(
                segments=segments,
                speaker_count=len(speaker_ids),
                audio_duration=audio_duration,
                model_name=self.model_name,
                overlap_detected=self._check_overlap(segments),
            )

            logger.info(
                "说话人分离完成",
                speakers=result.speaker_count,
                segments=len(segments),
                duration=audio_duration,
            )

            return result

        except ImportError:
            raise DiarizerError(
                "未安装 pyannote.audio，请运行: pip install pyannote.audio"
            )
        except Exception as e:
            logger.error("说话人分离失败", error=str(e))
            raise DiarizerError(f"说话人分离失败: {e}") from e

    def _load_pipeline(self) -> None:
        """加载 pyannote 预训练模型."""
        try:
            from pyannote.audio import Pipeline

            load_params = {}
            if self.hf_token:
                load_params["use_auth_token"] = self.hf_token

            logger.info("正在加载说话人分离模型", model=self.model_name)
            self._pipeline = Pipeline.from_pretrained(self.model_name, **load_params)

            # 自动检测设备
            if self._device == "auto":
                try:
                    import torch

                    if torch.cuda.is_available():
                        self._pipeline.to(torch.device("cuda"))
                        logger.info("说话人分离模型已加载到 GPU")
                    else:
                        logger.info("说话人分离模型使用 CPU")
                except ImportError:
                    pass

        except ImportError:
            raise DiarizerError(
                "未安装 pyannote.audio，请运行: pip install pyannote.audio"
            )

    def _check_overlap(self, segments: list[SpeakerSegment]) -> bool:
        """检查是否存在交叉对话.

        Args:
            segments: 说话人片段列表

        Returns:
            是否存在交叉对话
        """
        if len(segments) < 2:
            return False

        sorted_segments = sorted(segments, key=lambda s: s.start_time)

        for i in range(len(sorted_segments) - 1):
            current = sorted_segments[i]
            next_seg = sorted_segments[i + 1]

            if (
                current.speaker_id != next_seg.speaker_id
                and current.end_time > next_seg.start_time
            ):
                return True

        return False

    def align_with_transcript(
        self,
        transcript_segments: list[Any],
        diarization: DiarizationResult,
    ) -> list[dict[str, Any]]:
        """将说话人标签对齐到转录片段.

        使用时间轴匹配算法，将每个转录片段映射到最可能的说话人.

        Args:
            transcript_segments: 转录片段列表（需包含 start_time, end_time）
            diarization: 说话人分离结果

        Returns:
            带说话人标签的转录片段列表
        """
        aligned = []

        for seg in transcript_segments:
            # 找到与该片段重叠最多的说话人段
            best_speaker = self._find_best_matching_speaker(seg, diarization)

            aligned.append(
                {
                    "start_time": getattr(seg, "start_time", 0.0),
                    "end_time": getattr(seg, "end_time", 0.0),
                    "text": getattr(seg, "text", ""),
                    "speaker": best_speaker,
                    "confidence": getattr(seg, "confidence", None),
                }
            )

        return aligned

    def _find_best_matching_speaker(
        self,
        segment: Any,
        diarization: DiarizationResult,
    ) -> str | None:
        """找到与转录片段最匹配的说话人.

        基于时间重叠度选择最佳说话人.

        Args:
            segment: 转录片段
            diarization: 说话人分离结果

        Returns:
            最佳匹配的说话人 ID，如果没有匹配则返回 None
        """
        start = getattr(segment, "start_time", 0.0)
        end = getattr(segment, "end_time", 0.0)
        seg_duration = end - start

        if seg_duration <= 0:
            return None

        best_speaker = None
        best_overlap = 0.0

        for diag_seg in diarization.segments:
            # 计算时间重叠
            overlap_start = max(start, diag_seg.start_time)
            overlap_end = min(end, diag_seg.end_time)
            overlap = max(0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = diag_seg.speaker_id

        # 只有重叠度超过阈值才返回说话人标签
        if best_overlap / seg_duration > 0.3:
            return best_speaker

        return None

    def extract_speaker_embeddings(
        self,
        audio_path: Path,
        diarization: DiarizationResult | None = None,
    ) -> dict[str, Any]:
        """提取说话人嵌入向量（用于说话人注册和识别）.

        Args:
            audio_path: 音频文件路径
            diarization: 说话人分离结果（可选，如无则自动执行）

        Returns:
            说话人嵌入向字典 {speaker_id: embedding_array}
        """
        try:
            import numpy as np
            from speechbrain.pretrained import EncoderClassifier

            if diarization is None:
                diarization = self.diarize(audio_path)

            # 加载说话人嵌入模型
            classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                run_opts={"device": self._device if self._device != "auto" else "cpu"},
            )

            embeddings = {}

            for speaker_id in diarization.unique_speakers:
                speaker_segments = diarization.get_segments_by_speaker(speaker_id)

                if not speaker_segments:
                    continue

                # 合并该说话人的所有片段，提取平均嵌入
                segment_embeddings = []

                for seg in speaker_segments:
                    if seg.duration < 1.0:
                        continue

                    try:
                        # 提取片段嵌入
                        embedding = self._extract_segment_embedding(
                            classifier, audio_path, seg
                        )
                        if embedding is not None:
                            segment_embeddings.append(embedding)
                    except Exception as e:
                        logger.warning(
                            f"提取 {speaker_id} 片段嵌入失败: {e}"
                        )

                if segment_embeddings:
                    # 计算平均嵌入
                    avg_embedding = np.mean(segment_embeddings, axis=0)
                    embeddings[speaker_id] = avg_embedding.tolist()

            self._speaker_embeddings = embeddings
            logger.info(
                "说话人嵌入提取完成",
                speakers=len(embeddings),
            )

            return embeddings

        except ImportError:
            raise DiarizerError(
                "未安装 speechbrain，请运行: pip install speechbrain"
            )
        except Exception as e:
            logger.error("说话人嵌入提取失败", error=str(e))
            raise DiarizerError(f"说话人嵌入提取失败: {e}") from e

    def _extract_segment_embedding(
        self,
        classifier: Any,
        audio_path: Path,
        segment: SpeakerSegment,
    ) -> Any | None:
        """提取单个片段的说话人嵌入.

        Args:
            classifier: speechbrain 分类器
            audio_path: 音频文件路径
            segment: 说话人片段

        Returns:
            嵌入向量，失败时返回 None
        """
        try:
            import torchaudio

            # 加载音频并截取片段
            waveform, sample_rate = torchaudio.load(str(audio_path))

            start_sample = int(segment.start_time * sample_rate)
            end_sample = int(segment.end_time * sample_rate)

            segment_waveform = waveform[:, start_sample:end_sample]

            # 计算嵌入
            with torch.no_grad():
                embeddings = classifier.encode_batch(segment_waveform)

            return embeddings.squeeze().cpu().numpy()

        except Exception as e:
            logger.warning(f"提取片段嵌入失败: {e}")
            return None

    def cleanup(self) -> None:
        """清理模型资源."""
        self._pipeline = None
        self._speaker_embeddings = {}
        logger.info("说话人分离器资源已清理")


# =============================================================================
# 对齐引擎 — 用于 STT 结果与 Diarization 结果的时间轴对齐
# =============================================================================

class AlignmentEngine:
    """STT 文本与说话人标签对齐引擎.

    当使用不支持原生 diarization 的 STT 引擎（如 Whisper）时，
    需要将 pyannote 的说话人分离结果与 STT 转录结果进行时间轴对齐。
    """

    def __init__(self, overlap_threshold: float = 0.3) -> None:
        """初始化对齐引擎.

        Args:
            overlap_threshold: 最小重叠比例阈值（0-1）
        """
        self.overlap_threshold = overlap_threshold

    def align(
        self,
        transcript_segments: list[Any],
        diarization: DiarizationResult,
    ) -> list[dict[str, Any]]:
        """对齐转录片段与说话人标签.

        Args:
            transcript_segments: 转录片段列表
            diarization: 说话人分离结果

        Returns:
            带说话人标签的转录片段
        """
        aligned = []

        for seg in transcript_segments:
            speaker = self._find_best_match(seg, diarization)
            aligned.append(
                {
                    "start_time": getattr(seg, "start_time", 0.0),
                    "end_time": getattr(seg, "end_time", 0.0),
                    "text": getattr(seg, "text", ""),
                    "speaker": speaker,
                    "confidence": getattr(seg, "confidence", None),
                    "emotion": getattr(seg, "emotion", None),
                    "audio_event": getattr(seg, "audio_event", None),
                }
            )

        return aligned

    def _find_best_match(
        self,
        segment: Any,
        diarization: DiarizationResult,
    ) -> str | None:
        """找到最佳匹配的说话人.

        Args:
            segment: 转录片段
            diarization: 说话人分离结果

        Returns:
            说话人 ID 或 None
        """
        start = getattr(segment, "start_time", 0.0)
        end = getattr(segment, "end_time", 0.0)
        seg_duration = end - start

        if seg_duration <= 0:
            return None

        best_speaker = None
        best_overlap = 0.0

        for diag_seg in diarization.segments:
            overlap_start = max(start, diag_seg.start_time)
            overlap_end = min(end, diag_seg.end_time)
            overlap = max(0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = diag_seg.speaker_id

        if best_overlap / seg_duration > self.overlap_threshold:
            return best_speaker

        return None
