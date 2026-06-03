"""图文笔记数据模型."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from models.xiaohongshu import XiaohongshuNote


class VisualXiaohongshuNote(BaseModel):
    """图文笔记模型.

    包含文字笔记和配套图片的完整小红书笔记。
    """

    # 文字笔记
    text_note: XiaohongshuNote = Field(..., description="文字笔记内容")

    # 图片列表（按顺序：封面→内容页→总结页）
    image_paths: list[Path] = Field(default_factory=list, description="生成的图片路径列表")

    # 结构化内容（用于图片生成）
    structured_content: dict = Field(default_factory=dict, description="结构化内容数据")

    # 来源信息
    source_info: dict = Field(default_factory=dict, description="播客来源信息")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    style: str = Field(default="blue", description="配色方案")

    def format_text_for_editor(self) -> str:
        """格式化适合小红书编辑器粘贴的文字内容.

        文字作为图片的辅助说明，简练随和。

        Returns:
            格式化后的文字内容
        """
        intro = self.structured_content.get("introduction", "")
        conclusion = self.structured_content.get("conclusion", "")
        tags = self.structured_content.get("tags", [])

        lines = []

        # 开头钩子
        if intro:
            lines.append(intro)
            lines.append("")

        # 内容引导
        lines.append("👆 左滑查看详细笔记，我把核心观点都整理好了")
        lines.append("")

        # 个人感悟
        if conclusion:
            lines.append(conclusion)
            lines.append("")

        # 互动引导
        lines.append("你去听这期播客了吗？评论区聊聊你的看法 👇")
        lines.append("")

        # 标签
        if tags:
            tags_str = " ".join(f"#{tag}" for tag in tags)
            lines.append(tags_str)

        return "\n".join(lines)

    def save_complete_note(self, output_dir: Path) -> Path:
        """保存完整笔记（文字+图片清单）.

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(
            c for c in self.text_note.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:30]

        output_path = output_dir / f"{safe_title}_visual_note.md"

        lines = [
            f"# {self.text_note.title}",
            f"",
            f"## 文字内容（粘贴到小红书编辑器）",
            f"",
            self.format_text_for_editor(),
            f"",
            f"## 图片列表（按顺序上传）",
            f"",
        ]

        for idx, img_path in enumerate(self.image_paths, 1):
            lines.append(f"{idx}. {img_path.name}")

        lines.extend([
            f"",
            f"---",
            f"",
            f"字数: {self.text_note.word_count}",
            f"图片数: {len(self.image_paths)}",
            f"配色: {self.style}",
            f"生成时间: {self.created_at.isoformat()}",
        ])

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
