"""内容处理模块测试."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.content_processor import ContentProcessor, ContentProcessorError
from models.transcript import Transcript
from models.xiaohongshu import XiaohongshuNote


class TestContentProcessor:
    """内容处理器测试类."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """创建模拟的 LLM 服务."""
        llm = MagicMock()
        llm.generate.return_value = """
# 测试标题

这是正文内容，包含一些干货要点。

💡 核心要点：
• 要点一
• 要点二

🔖 #标签1 #标签2 #标签3
"""
        return llm

    @pytest.fixture
    def processor(self, mock_llm: MagicMock) -> ContentProcessor:
        """创建测试用的内容处理器."""
        return ContentProcessor(llm_service=mock_llm)

    def test_preprocess_text_removes_fillers(self, processor: ContentProcessor) -> None:
        """测试预处理去除口头禅."""
        text = "嗯，这个那个，我觉得就是，首先我们要知道"
        result = processor._preprocess_text(text)
        assert "嗯" not in result
        assert "那个" not in result
        assert "就是" not in result

    def test_preprocess_text_removes_extra_whitespace(self, processor: ContentProcessor) -> None:
        """测试预处理去除多余空白."""
        text = "  段落1   \n\n   段落2  "
        result = processor._preprocess_text(text)
        assert "  " not in result
        assert result.startswith("段落1")

    def test_fallback_extraction(self, processor: ContentProcessor) -> None:
        """测试备用信息提取."""
        text = "这是一个关于个人成长的测试文本，包含了非常丰富的内容。包含多个句子的长段落，每个句子都有一些值得关注的重要内容值得记录。"
        result = processor._fallback_extraction(text)

        assert "theme" in result
        assert "key_points" in result
        assert "tags" in result
        assert len(result["key_points"]) > 0
        assert len(result["tags"]) == 3

    def test_quality_check_word_count_low(self, processor: ContentProcessor) -> None:
        """测试字数不足的质量检查."""
        note = XiaohongshuNote(
            title="测试",
            content="短内容",
            tags=["标签1", "标签2", "标签3"],
            word_count=10,
        )
        result = processor._quality_check(note)
        assert result.word_count == 10  # 不会修改，只记录警告

    def test_quality_check_tags_truncate(self, processor: ContentProcessor) -> None:
        """测试标签过多时的截断."""
        note = XiaohongshuNote(
            title="测试",
            content="这是正文内容，字数足够多。" * 20,
            tags=["标签1", "标签2", "标签3", "标签4", "标签5", "标签6"],
            word_count=200,
        )
        result = processor._quality_check(note)
        assert len(result.tags) == 5  # 最多 5 个标签

    def test_quality_check_title_truncate(self, processor: ContentProcessor) -> None:
        """测试标题过长时的截断."""
        note = XiaohongshuNote(
            title="原始标题",
            content="这是正文内容，字数足够多。" * 20,
            tags=["标签1", "标签2", "标签3"],
            word_count=200,
        )
        # 手动设置超长标题来测试截断逻辑
        note.title = "这是一个非常长的标题，超过了二十个字的限制"
        result = processor._quality_check(note)
        assert len(result.title) <= 20

    def test_parse_note_content_with_hash_title(self, processor: ContentProcessor) -> None:
        """测试解析带 # 标题的内容."""
        content = "# 这是标题\n\n这是正文内容。"
        result = processor._parse_note_content(
            content=content,
            podcast_name="测试播客",
            episode_title="第1期",
            tags=["标签1"],
        )
        assert result.title == "这是标题"
        assert "这是正文内容" in result.content

    def test_parse_note_content_without_hash(self, processor: ContentProcessor) -> None:
        """测试解析不带 # 标题的内容."""
        content = "这是标题\n\n这是正文内容。"
        result = processor._parse_note_content(
            content=content,
            podcast_name="测试播客",
            episode_title="第1期",
            tags=["标签1"],
        )
        assert result.title == "这是标题"


class TestXiaohongshuNoteConstraints:
    """小红书笔记约束测试."""

    def test_note_constraints_values(self) -> None:
        """测试约束值设置."""
        from core.content_processor import ContentProcessor

        assert ContentProcessor.NOTE_CONSTRAINTS["min_word_count"] == 100
        assert ContentProcessor.NOTE_CONSTRAINTS["max_word_count"] == 800
        assert ContentProcessor.NOTE_CONSTRAINTS["min_tags"] == 3
        assert ContentProcessor.NOTE_CONSTRAINTS["max_tags"] == 5
        assert ContentProcessor.NOTE_CONSTRAINTS["title_max_length"] == 20
