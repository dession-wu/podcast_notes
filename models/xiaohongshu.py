"""小红书笔记数据模型."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class XiaohongshuNote(BaseModel):
    """小红书笔记模型."""

    # 内容
    title: str = Field(..., description="笔记标题（钩子）", max_length=50)
    content: str = Field(..., description="笔记正文", max_length=10000)
    tags: list[str] = Field(default_factory=list, description="话题标签")

    # 来源信息（合规要求）
    source_podcast: str | None = Field(default=None, description="来源播客名称")
    source_episode: str | None = Field(default=None, description="来源单集标题")
    source_attribution: str = Field(
        default="",
        description="来源标注文案",
    )

    # 封面
    cover_image_path: Path | None = Field(default=None, description="封面图路径")
    cover_prompt: str | None = Field(default=None, description="封面图生成提示词")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    word_count: int = Field(default=0, description="正文字数")

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list[str] | str) -> list[str]:
        """标准化标签格式."""
        if isinstance(v, str):
            # 从逗号或空格分隔的字符串解析
            tags = [t.strip() for t in v.replace("，", ",").split(",") if t.strip()]
            return tags
        return v

    @model_validator(mode="after")
    def ensure_source_attribution(self) -> "XiaohongshuNote":
        """确保内容包含来源标注（在所有字段赋值后执行）."""
        source = self.source_podcast
        if source and "本文灵感/内容提炼自播客" not in self.content:
            # 自动在开头添加来源标注
            attribution = f"🎙️ 本文灵感/内容提炼自播客《{source}》"
            if self.source_episode:
                attribution += f" — {self.source_episode}"
            self.content = f"{attribution}\n\n{self.content}"

        # 同步 source_attribution 字段
        if not self.source_attribution and source:
            self.source_attribution = f"🎙️ 本文灵感/内容提炼自播客《{source}》"
            if self.source_episode:
                self.source_attribution += f" — {self.source_episode}"

        return self

    def format_full_text(self) -> str:
        """格式化完整笔记文本（含标签）."""
        lines = [self.content]

        if self.tags:
            tags_str = " ".join(f"#{tag}" for tag in self.tags)
            lines.append(f"\n{tags_str}")

        return "\n".join(lines)

    def save_to_file(self, path: Path) -> None:
        """保存笔记到文件.

        Args:
            path: 输出文件路径
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# {self.title}",
            f"",
            self.format_full_text(),
            f"",
            "---",
            f"",
            f"字数: {self.word_count}",
            f"标签: {', '.join(self.tags)}",
            f"来源: {self.source_podcast or '未知'}",
            f"生成时间: {self.created_at.isoformat()}",
        ]

        if self.cover_image_path:
            lines.append(f"封面图: {self.cover_image_path}")

        path.write_text("\n".join(lines), encoding="utf-8")

    def to_txt(self) -> str:
        """Export note as plain text."""
        lines = [
            self.title,
            "",
            self.content,
            "",
            "Tags: " + " ".join(f"#{t}" for t in self.tags),
            "",
            f"Source: {self.source_podcast or 'Unknown'}",
        ]
        return "\n".join(lines)

    def to_json(self) -> str:
        """Export note as structured JSON."""
        return self.model_dump_json(indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        return f"小红书笔记《{self.title}》({self.word_count} 字)"
