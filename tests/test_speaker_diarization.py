"""说话人分离功能测试."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.speaker_diarizer import (
    AlignmentEngine,
    DiarizationResult,
    DiarizerError,
    SpeakerDiarizer,
    SpeakerSegment,
)
from core.speaker_registry import (
    SpeakerInfo,
    SpeakerMappingManager,
    SpeakerRegistry,
    SpeakerRegistryError,
)
from models.transcript import Transcript, TranscriptSegment


# =============================================================================
# SpeakerSegment 测试
# =============================================================================

class TestSpeakerSegment:
    """说话人片段模型测试."""

    def test_duration(self) -> None:
        """测试时长计算."""
        seg = SpeakerSegment(
            start_time=10.0,
            end_time=15.5,
            speaker_id="SPEAKER_0",
        )
        assert seg.duration == 5.5

    def test_default_confidence(self) -> None:
        """测试默认置信度."""
        seg = SpeakerSegment(
            start_time=0.0,
            end_time=5.0,
            speaker_id="SPEAKER_0",
        )
        assert seg.confidence == 1.0


# =============================================================================
# DiarizationResult 测试
# =============================================================================

class TestDiarizationResult:
    """说话人分离结果模型测试."""

    def test_unique_speakers(self) -> None:
        """测试唯一说话人列表."""
        result = DiarizationResult(
            segments=[
                SpeakerSegment(0.0, 5.0, "SPEAKER_0"),
                SpeakerSegment(5.0, 10.0, "SPEAKER_1"),
                SpeakerSegment(10.0, 15.0, "SPEAKER_0"),
                SpeakerSegment(15.0, 20.0, "SPEAKER_0"),
            ],
            speaker_count=2,
        )
        assert result.unique_speakers == ["SPEAKER_0", "SPEAKER_1"]

    def test_get_segments_by_speaker(self) -> None:
        """测试按说话人获取片段."""
        result = DiarizationResult(
            segments=[
                SpeakerSegment(0.0, 5.0, "SPEAKER_0"),
                SpeakerSegment(5.0, 10.0, "SPEAKER_1"),
                SpeakerSegment(10.0, 15.0, "SPEAKER_0"),
            ],
            speaker_count=2,
        )
        segments = result.get_segments_by_speaker("SPEAKER_0")
        assert len(segments) == 2
        assert all(s.speaker_id == "SPEAKER_0" for s in segments)

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        result = DiarizationResult(
            segments=[
                SpeakerSegment(0.0, 5.0, "SPEAKER_0"),
            ],
            speaker_count=1,
            audio_duration=5.0,
            model_name="pyannote/speaker-diarization-3.1",
        )
        d = result.to_dict()
        assert d["speaker_count"] == 1
        assert d["audio_duration"] == 5.0
        assert d["model_name"] == "pyannote/speaker-diarization-3.1"
        assert len(d["segments"]) == 1

    def test_save_and_load(self, tmp_path: Path) -> None:
        """测试保存和加载."""
        result = DiarizationResult(
            segments=[
                SpeakerSegment(0.0, 5.0, "SPEAKER_0"),
                SpeakerSegment(5.0, 10.0, "SPEAKER_1"),
            ],
            speaker_count=2,
            audio_duration=10.0,
        )
        output_path = tmp_path / "diarization.json"
        result.save_to_file(output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["speaker_count"] == 2


# =============================================================================
# SpeakerDiarizer 测试
# =============================================================================

class TestSpeakerDiarizer:
    """说话人分离器测试."""

    def test_init_with_config(self) -> None:
        """测试初始化配置."""
        diarizer = SpeakerDiarizer(
            model_name="custom/model",
            max_speakers=3,
            hf_token="test_token",
        )
        assert diarizer.model_name == "custom/model"
        assert diarizer.max_speakers == 3
        assert diarizer.hf_token == "test_token"

    def test_init_default(self) -> None:
        """测试默认初始化."""
        diarizer = SpeakerDiarizer()
        assert "pyannote" in diarizer.model_name
        assert diarizer.max_speakers is None

    def test_diarize_file_not_exists(self) -> None:
        """测试文件不存在的错误处理."""
        diarizer = SpeakerDiarizer()
        with pytest.raises(DiarizerError) as exc_info:
            diarizer.diarize(Path("/nonexistent/audio.mp3"))
        assert "音频文件不存在" in str(exc_info.value)

    def test_check_overlap_no_overlap(self) -> None:
        """测试无交叉对话检测."""
        segments = [
            SpeakerSegment(0.0, 5.0, "SPEAKER_0"),
            SpeakerSegment(5.0, 10.0, "SPEAKER_1"),
            SpeakerSegment(10.0, 15.0, "SPEAKER_0"),
        ]
        assert not SpeakerDiarizer()._check_overlap(segments)

    def test_check_overlap_with_overlap(self) -> None:
        """测试有交叉对话检测."""
        segments = [
            SpeakerSegment(0.0, 6.0, "SPEAKER_0"),
            SpeakerSegment(5.0, 10.0, "SPEAKER_1"),
        ]
        assert SpeakerDiarizer()._check_overlap(segments)

    def test_check_overlap_single_segment(self) -> None:
        """测试单片段无交叉."""
        segments = [
            SpeakerSegment(0.0, 5.0, "SPEAKER_0"),
        ]
        assert not SpeakerDiarizer()._check_overlap(segments)


# =============================================================================
# AlignmentEngine 测试
# =============================================================================

class TestAlignmentEngine:
    """对齐引擎测试."""

    @staticmethod
    def _create_diarization_result() -> DiarizationResult:
        """创建测试用说话人分离结果."""
        return DiarizationResult(
            segments=[
                SpeakerSegment(0.0, 10.0, "SPEAKER_0"),
                SpeakerSegment(10.0, 20.0, "SPEAKER_1"),
                SpeakerSegment(20.0, 30.0, "SPEAKER_0"),
            ],
            speaker_count=2,
        )

    def test_align_with_perfect_match(self) -> None:
        """测试完美匹配对齐."""
        engine = AlignmentEngine(overlap_threshold=0.3)
        transcript_segments = [
            MagicMock(start_time=2.0, end_time=8.0, text="说话人0的内容", confidence=0.9),
        ]
        diarization = self._create_diarization_result()

        aligned = engine.align(transcript_segments, diarization)

        assert len(aligned) == 1
        assert aligned[0]["speaker"] == "SPEAKER_0"
        assert aligned[0]["text"] == "说话人0的内容"

    def test_align_with_different_speakers(self) -> None:
        """测试不同说话人对齐."""
        engine = AlignmentEngine(overlap_threshold=0.3)
        transcript_segments = [
            MagicMock(start_time=2.0, end_time=8.0, text="说话人0的内容", confidence=0.9),
            MagicMock(start_time=12.0, end_time=18.0, text="说话人1的内容", confidence=0.85),
        ]
        diarization = self._create_diarization_result()

        aligned = engine.align(transcript_segments, diarization)

        assert aligned[0]["speaker"] == "SPEAKER_0"
        assert aligned[1]["speaker"] == "SPEAKER_1"

    def test_align_no_match_below_threshold(self) -> None:
        """测试低于阈值的匹配."""
        # 创建一个跨边界的片段，与单个说话人段的重叠比例较低
        engine = AlignmentEngine(overlap_threshold=0.8)
        transcript_segments = [
            # 这个片段从 8.0 到 12.0，横跨 SPEAKER_0 和 SPEAKER_1
            # 与 SPEAKER_0 的重叠: 8.0-10.0 = 2.0s, 片段总长 4.0s, 比例 0.5
            # 与 SPEAKER_1 的重叠: 10.0-12.0 = 2.0s, 片段总长 4.0s, 比例 0.5
            # 都不满足 0.8 阈值
            MagicMock(start_time=8.0, end_time=12.0, text="跨边界片段", confidence=0.9),
        ]
        diarization = self._create_diarization_result()

        aligned = engine.align(transcript_segments, diarization)

        assert aligned[0]["speaker"] is None

    def test_align_empty_transcript(self) -> None:
        """测试空转录对齐."""
        engine = AlignmentEngine()
        aligned = engine.align([], self._create_diarization_result())
        assert aligned == []

    def test_align_preserves_other_fields(self) -> None:
        """测试对齐保留其他字段."""
        engine = AlignmentEngine(overlap_threshold=0.3)
        transcript_segments = [
            MagicMock(
                start_time=2.0,
                end_time=8.0,
                text="内容",
                confidence=0.9,
                emotion="EXCITED",
                audio_event="Speech",
            ),
        ]
        diarization = self._create_diarization_result()

        aligned = engine.align(transcript_segments, diarization)

        assert aligned[0]["emotion"] == "EXCITED"
        assert aligned[0]["audio_event"] == "Speech"
        assert aligned[0]["confidence"] == 0.9


# =============================================================================
# SpeakerRegistry 测试
# =============================================================================

class TestSpeakerRegistry:
    """说话人注册系统测试."""

    def test_register_speaker(self, tmp_path: Path) -> None:
        """测试注册说话人."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        speaker = registry.register_speaker(
            speaker_id="SPEAKER_0",
            name="张三",
            podcast_name="测试播客",
            role="host",
        )

        assert speaker.speaker_id == "SPEAKER_0"
        assert speaker.name == "张三"
        assert speaker.podcast_name == "测试播客"
        assert speaker.role == "host"

    def test_register_duplicate_updates(self, tmp_path: Path) -> None:
        """测试重复注册会更新."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三", podcast_name="播客1")

        # 重复注册
        speaker = registry.register_speaker("SPEAKER_0", "张三", podcast_name="播客2")
        assert speaker.podcast_name == "播客2"

    def test_identify_speaker_no_embeddings(self, tmp_path: Path) -> None:
        """测试无嵌入向量时无法识别."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三")

        result = registry.identify_speaker([0.1, 0.2, 0.3])
        assert result is None

    def test_get_all_speakers(self, tmp_path: Path) -> None:
        """测试获取所有说话人."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三", podcast_name="播客A", role="host")
        registry.register_speaker("SPEAKER_1", "李四", podcast_name="播客B", role="guest")

        all_speakers = registry.get_all_speakers()
        assert len(all_speakers) == 2

    def test_get_speakers_by_podcast(self, tmp_path: Path) -> None:
        """测试按播客筛选说话人."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三", podcast_name="播客A")
        registry.register_speaker("SPEAKER_1", "李四", podcast_name="播客B")

        speakers = registry.get_all_speakers(podcast_name="播客A")
        assert len(speakers) == 1
        assert speakers[0].name == "张三"

    def test_get_speakers_by_role(self, tmp_path: Path) -> None:
        """测试按角色筛选说话人."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三", role="host")
        registry.register_speaker("SPEAKER_1", "李四", role="guest")

        hosts = registry.get_all_speakers(role="host")
        assert len(hosts) == 1

    def test_get_speaker(self, tmp_path: Path) -> None:
        """测试获取指定说话人."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三")

        speaker = registry.get_speaker("SPEAKER_0")
        assert speaker is not None
        assert speaker.name == "张三"

        assert registry.get_speaker("NONEXISTENT") is None

    def test_update_speaker_name(self, tmp_path: Path) -> None:
        """测试更新说话人名称."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三")

        updated = registry.update_speaker_name("SPEAKER_0", "张主持人")
        assert updated is not None
        assert updated.name == "张主持人"

        # 验证已保存
        registry2 = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        assert registry2.get_speaker("SPEAKER_0").name == "张主持人"

    def test_remove_speaker(self, tmp_path: Path) -> None:
        """测试删除说话人."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry.register_speaker("SPEAKER_0", "张三")

        assert registry.remove_speaker("SPEAKER_0") is True
        assert registry.get_speaker("SPEAKER_0") is None
        assert registry.remove_speaker("NONEXISTENT") is False

    def test_export_and_import(self, tmp_path: Path) -> None:
        """测试导出和导入."""
        registry1 = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        registry1.register_speaker("SPEAKER_0", "张三", podcast_name="测试播客")

        export_path = tmp_path / "export.json"
        registry1.export_registry(export_path)
        assert export_path.exists()

        # 导入到新实例
        registry2 = SpeakerRegistry(storage_path=tmp_path / "registry2.json")
        count = registry2.import_registry(export_path)
        assert count == 1
        assert registry2.get_speaker("SPEAKER_0").name == "张三"

    def test_import_nonexistent_file(self, tmp_path: Path) -> None:
        """测试导入不存在文件."""
        registry = SpeakerRegistry(storage_path=tmp_path / "registry.json")
        with pytest.raises(SpeakerRegistryError):
            registry.import_registry(tmp_path / "nonexistent.json")

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """测试跨实例持久化."""
        storage = tmp_path / "registry.json"

        registry1 = SpeakerRegistry(storage_path=storage)
        registry1.register_speaker("SPEAKER_0", "张三")

        registry2 = SpeakerRegistry(storage_path=storage)
        assert registry2.get_speaker("SPEAKER_0") is not None
        assert registry2.get_speaker("SPEAKER_0").name == "张三"


# =============================================================================
# SpeakerMappingManager 测试
# =============================================================================

class TestSpeakerMappingManager:
    """说话人标签映射管理器测试."""

    def test_set_and_get_mapping(self, tmp_path: Path) -> None:
        """测试设置和获取映射."""
        manager = SpeakerMappingManager(storage_path=tmp_path / "mappings.json")
        manager.set_mapping("SPEAKER_0", "张三")
        assert manager.get_mapping("SPEAKER_0") == "张三"

    def test_get_nonexistent_mapping(self, tmp_path: Path) -> None:
        """测试获取不存在的映射."""
        manager = SpeakerMappingManager(storage_path=tmp_path / "mappings.json")
        assert manager.get_mapping("NONEXISTENT") is None

    def test_clear_mappings(self, tmp_path: Path) -> None:
        """测试清除映射."""
        manager = SpeakerMappingManager(storage_path=tmp_path / "mappings.json")
        manager.set_mapping("SPEAKER_0", "张三")
        manager.set_mapping("SPEAKER_1", "李四")

        manager.clear_mappings()

        assert manager.get_all_mappings() == {}
        assert manager.get_mapping("SPEAKER_0") is None

    def test_persistence(self, tmp_path: Path) -> None:
        """测试持久化."""
        storage = tmp_path / "mappings.json"

        manager1 = SpeakerMappingManager(storage_path=storage)
        manager1.set_mapping("SPEAKER_0", "张三")

        manager2 = SpeakerMappingManager(storage_path=storage)
        assert manager2.get_mapping("SPEAKER_0") == "张三"

    def test_get_all_mappings(self, tmp_path: Path) -> None:
        """测试获取所有映射."""
        manager = SpeakerMappingManager(storage_path=tmp_path / "mappings.json")
        manager.set_mapping("SPEAKER_0", "张三")
        manager.set_mapping("SPEAKER_1", "李四")

        all_mappings = manager.get_all_mappings()
        assert len(all_mappings) == 2
        assert all_mappings["SPEAKER_0"] == "张三"
        assert all_mappings["SPEAKER_1"] == "李四"
