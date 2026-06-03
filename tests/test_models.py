"""数据模型测试."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from models.podcast import PodcastEpisode
from models.transcript import Transcript, TranscriptSegment
from models.xiaohongshu import XiaohongshuNote


class TestTranscriptSegment:
    """转录片段模型测试."""

    def test_duration(self) -> None:
        """测试时长计算."""
        segment = TranscriptSegment(
            start_time=10.0,
            end_time=15.5,
            text="测试文本",
        )
        assert segment.duration == 5.5

    def test_format_timestamp_short(self) -> None:
        """测试短时间戳格式化."""
        segment = TranscriptSegment(
            start_time=65.0,
            end_time=70.0,
            text="测试",
        )
        assert segment.format_timestamp() == "[01:05]"

    def test_format_timestamp_long(self) -> None:
        """测试长时间戳格式化."""
        segment = TranscriptSegment(
            start_time=3661.0,
            end_time=3665.0,
            text="测试",
        )
        assert segment.format_timestamp() == "[01:01:01]"

    def test_str_with_speaker(self) -> None:
        """测试带说话人的字符串表示."""
        segment = TranscriptSegment(
            start_time=10.0,
            end_time=15.0,
            text="你好",
            speaker="主持人",
        )
        assert str(segment) == "[00:10] 主持人: 你好"

    def test_str_without_speaker(self) -> None:
        """测试不带说话人的字符串表示."""
        segment = TranscriptSegment(
            start_time=10.0,
            end_time=15.0,
            text="你好",
        )
        assert str(segment) == "[00:10] 你好"

    def test_sensevoice_fields(self) -> None:
        """测试 SenseVoice 扩展字段."""
        segment = TranscriptSegment(
            start_time=10.0,
            end_time=15.0,
            text="这是一个激动人心的时刻",
            emotion="EXCITED",
            audio_event="Speech",
        )
        assert segment.emotion == "EXCITED"
        assert segment.audio_event == "Speech"


class TestTranscript:
    """转录文本模型测试."""

    def test_text_property(self) -> None:
        """测试文本属性."""
        transcript = Transcript(
            episode_title="测试单集",
            segments=[
                TranscriptSegment(start_time=0.0, end_time=5.0, text="第一段"),
                TranscriptSegment(start_time=5.0, end_time=10.0, text="第二段"),
            ],
        )
        assert transcript.text == "第一段 第二段"

    def test_text_property_with_full_text(self) -> None:
        """测试优先使用 full_text."""
        transcript = Transcript(
            episode_title="测试单集",
            full_text="完整文本",
            segments=[
                TranscriptSegment(start_time=0.0, end_time=5.0, text="第一段"),
            ],
        )
        assert transcript.text == "完整文本"

    def test_word_count_chinese(self) -> None:
        """测试中文字数统计."""
        transcript = Transcript(
            episode_title="测试",
            full_text="这是一个测试文本",
        )
        assert transcript.word_count == 8  # 8 个中文字符

    def test_word_count_mixed(self) -> None:
        """测试中英混合字数统计."""
        transcript = Transcript(
            episode_title="测试",
            full_text="这是 test 文本",
        )
        # 中文字符: 4, 英文单词: 1
        assert transcript.word_count == 5

    def test_get_text_by_time_range(self) -> None:
        """测试按时间范围获取文本."""
        transcript = Transcript(
            episode_title="测试",
            segments=[
                TranscriptSegment(start_time=0.0, end_time=5.0, text="第一段"),
                TranscriptSegment(start_time=5.0, end_time=10.0, text="第二段"),
                TranscriptSegment(start_time=10.0, end_time=15.0, text="第三段"),
            ],
        )
        result = transcript.get_text_by_time_range(4.0, 11.0)
        assert result == "第二段"

    def test_save_to_file(self, tmp_path: Path) -> None:
        """测试保存到文件."""
        transcript = Transcript(
            episode_title="测试单集",
            podcast_name="测试播客",
            language="zh",
            duration_seconds=120.0,
            stt_provider="whisper",
            segments=[
                TranscriptSegment(start_time=0.0, end_time=5.0, text="第一段"),
            ],
        )
        output_path = tmp_path / "test_transcript.md"
        transcript.save_to_file(output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# 测试单集" in content
        assert "播客: 测试播客" in content
        assert "第一段" in content


class TestXiaohongshuNote:
    """小红书笔记模型测试."""

    def test_normalize_tags_from_string(self) -> None:
        """测试从字符串解析标签."""
        note = XiaohongshuNote(
            title="测试",
            content="内容",
            tags="标签1, 标签2, 标签3",
        )
        assert note.tags == ["标签1", "标签2", "标签3"]

    def test_normalize_tags_from_list(self) -> None:
        """测试从列表解析标签."""
        note = XiaohongshuNote(
            title="测试",
            content="内容",
            tags=["标签1", "标签2"],
        )
        assert note.tags == ["标签1", "标签2"]

    def test_source_attribution_auto_added(self) -> None:
        """测试自动添加来源标注."""
        note = XiaohongshuNote(
            title="测试",
            content="这是内容",
            source_podcast="测试播客",
            source_episode="第1期",
        )
        assert "🎙️ 本文灵感/内容提炼自播客《测试播客》" in note.content

    def test_source_attribution_preserved(self) -> None:
        """测试已有来源标注时不重复添加."""
        note = XiaohongshuNote(
            title="测试",
            content="🎙️ 本文灵感/内容提炼自播客《其他播客》\n\n这是内容",
            source_podcast="测试播客",
        )
        # 不应重复添加
        assert note.content.count("本文灵感/内容提炼自播客") == 1

    def test_format_full_text(self) -> None:
        """测试格式化完整文本."""
        note = XiaohongshuNote(
            title="测试标题",
            content="这是正文",
            tags=["标签1", "标签2"],
        )
        result = note.format_full_text()
        assert "这是正文" in result
        assert "#标签1" in result
        assert "#标签2" in result

    def test_save_to_file(self, tmp_path: Path) -> None:
        """测试保存到文件."""
        note = XiaohongshuNote(
            title="测试标题",
            content="这是正文",
            tags=["标签1"],
            source_podcast="测试播客",
            word_count=100,
        )
        output_path = tmp_path / "test_note.md"
        note.save_to_file(output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# 测试标题" in content
        assert "这是正文" in content
        assert "来源: 测试播客" in content
