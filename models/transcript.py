"""转录文本数据模型."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """转录文本片段模型（带时间戳）."""

    start_time: float = Field(..., description="开始时间（秒）")
    end_time: float = Field(..., description="结束时间（秒）")
    text: str = Field(..., description="转录文本")
    speaker: str | None = Field(default=None, description="说话人标识")
    confidence: float | None = Field(default=None, description="置信度 (0-1)")

    # SenseVoice 扩展字段
    emotion: str | None = Field(default=None, description="语音情感 (NEUTRAL/HAPPY/SAD/ANGRY/EXCITED)")
    audio_event: str | None = Field(default=None, description="音频事件 (Speech/Applause/Laughter/Cough等)")

    @property
    def duration(self) -> float:
        """片段时长（秒）."""
        return self.end_time - self.start_time

    def format_timestamp(self) -> str:
        """格式化时间戳为 [HH:MM:SS] 格式."""
        hours = int(self.start_time // 3600)
        minutes = int((self.start_time % 3600) // 60)
        seconds = int(self.start_time % 60)
        if hours > 0:
            return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        return f"[{minutes:02d}:{seconds:02d}]"

    def __str__(self) -> str:
        speaker_prefix = f"{self.speaker}: " if self.speaker else ""
        return f"{self.format_timestamp()} {speaker_prefix}{self.text}"


class Transcript(BaseModel):
    """完整转录文本模型."""

    # 来源信息
    episode_title: str = Field(..., description="播客单集标题")
    podcast_name: str | None = Field(default=None, description="播客名称")
    audio_path: Path | None = Field(default=None, description="音频文件路径")

    # 转录内容
    segments: list[TranscriptSegment] = Field(
        default_factory=list,
        description="转录片段列表",
    )
    full_text: str | None = Field(default=None, description="完整文本（拼接后）")

    # 元数据
    language: str | None = Field(default=None, description="检测到的语言")
    duration_seconds: float | None = Field(default=None, description="音频总时长")
    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="转录处理时间",
    )
    stt_provider: str = Field(default="unknown", description="使用的 STT 提供商")

    # 说话人分离相关
    diarization_enabled: bool = Field(
        default=False,
        description="是否启用了说话人分离",
    )
    diarization_result_path: str | None = Field(
        default=None,
        description="说话人分离结果文件路径",
    )
    speaker_count: int | None = Field(
        default=None,
        description="检测到的说话人数量",
    )

    # 内容分析结果（由 ContentProcessor 填充）
    theme: str | None = Field(default=None, description="核心主题")
    key_points: list[str] = Field(default_factory=list, description="核心要点")
    quotes: list[str] = Field(default_factory=list, description="金句摘录")

    @property
    def text(self) -> str:
        """获取完整文本（自动拼接）."""
        if self.full_text:
            return self.full_text
        return " ".join(seg.text for seg in self.segments)

    @property
    def word_count(self) -> int:
        """文本字数（中文字符 + 英文单词）."""
        text = self.text
        # 中文字符数
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        # 英文单词数（粗略统计）
        english_words = len([w for w in text.split() if w.isascii()])
        return chinese_chars + english_words

    @property
    def segment_count(self) -> int:
        """片段数量."""
        return len(self.segments)

    def get_text_by_time_range(self, start: float, end: float) -> str:
        """获取指定时间范围内的文本.

        Args:
            start: 开始时间（秒）
            end: 结束时间（秒）

        Returns:
            时间范围内的文本
        """
        relevant = [
            seg.text
            for seg in self.segments
            if seg.start_time >= start and seg.end_time <= end
        ]
        return " ".join(relevant)

    def save_to_file(self, path: Path) -> None:
        """保存转录文本到文件.

        Args:
            path: 输出文件路径
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# {self.episode_title}",
            f"",
            f"> 播客: {self.podcast_name or '未知'}",
            f"> 语言: {self.language or '未知'}",
            f"> 时长: {self.duration_seconds:.0f} 秒" if self.duration_seconds else "",
            f"> 处理时间: {self.processed_at.isoformat()}",
            f"> 引擎: {self.stt_provider}",
            f"",
            "---",
            f"",
        ]

        for seg in self.segments:
            lines.append(str(seg))

        path.write_text("\n".join(lines), encoding="utf-8")

    def to_txt(self) -> str:
        """Export transcript as plain text."""
        lines = [
            f"Title: {self.episode_title}",
            f"Podcast: {self.podcast_name or 'Unknown'}",
            f"Duration: {self.duration_seconds:.0f}s" if self.duration_seconds else "",
            "",
            "=" * 50,
            "",
        ]
        for seg in self.segments:
            speaker = f"[{seg.speaker}] " if seg.speaker else ""
            lines.append(f"{seg.format_timestamp()} {speaker}{seg.text}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Export transcript as structured JSON."""
        return self.model_dump_json(indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        return f"转录《{self.episode_title}》({self.word_count} 字, {self.segment_count} 段)"
