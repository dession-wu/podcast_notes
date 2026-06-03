"""播客数据模型."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PodcastEpisode(BaseModel):
    """播客单集模型."""

    title: str = Field(..., description="单集标题")
    description: str | None = Field(default=None, description="单集描述")
    audio_url: HttpUrl | str = Field(..., description="音频文件 URL")
    episode_number: int | None = Field(default=None, description="集数")
    publish_date: datetime | None = Field(default=None, description="发布日期")
    duration_seconds: int | None = Field(default=None, description="时长（秒）")
    guests: list[str] = Field(default_factory=list, description="嘉宾列表")
    local_audio_path: Path | None = Field(
        default=None,
        description="本地音频文件路径",
    )

    # 元数据
    feed_title: str | None = Field(default=None, description="所属播客名称")
    feed_url: HttpUrl | str | None = Field(default=None, description="RSS 源 URL")

    def get_safe_filename(self) -> str:
        """生成安全的文件名（用于本地存储）."""
        safe_title = "".join(
            c for c in self.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        if self.episode_number:
            return f"ep{self.episode_number:03d}_{safe_title[:50]}"
        return safe_title[:50]

    def get_podcast_name_from_title(self) -> str:
        """从单集标题中解析播客名称.

        某些 RSS 源的 title 格式为 "播客名 | 单集标题" 或 "播客名：单集标题"。

        Returns:
            解析出的播客名称，无法解析返回空字符串
        """
        import re

        # 匹配常见分隔符格式：播客名 | 标题、播客名：标题、播客名 - 标题
        patterns = [
            r"^([^|：:]+)[|：:]\s*",
            r"^([^-]+)\s+-\s+",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.title)
            if match:
                candidate = match.group(1).strip()
                # 过滤掉过短的匹配（避免误匹配）
                if len(candidate) >= 2:
                    return candidate

        return ""

    def extract_guests_from_description(self) -> list[str]:
        """从单集描述中提取嘉宾名称.

        使用常见关键词匹配：嘉宾、主讲、邀请、对话等。

        Returns:
            嘉宾名称列表
        """
        import re

        if not self.description:
            return []

        guests = []

        # 匹配模式："嘉宾：XXX"、"邀请 XXX"、"与 XXX 对话" 等
        patterns = [
            r"嘉宾[：:]\s*([^，。\n]+)",
            r"邀请[了]?\s*((?:[^，。\n\s]+\s+)*[^，。\n\s来]+)(?:\s*(?:来|作|为|做客|作客))",
            r"与\s*([^，。\n]+?)\s*对[话谈]",
            r"主讲[：:]\s*([^，。\n]+)",
            r"本期嘉宾[：:]\s*([^，。\n]+)",
            r"特邀\s*([^，。\n]+?)(?:嘉宾)?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, self.description)
            for match in matches:
                name = match.strip()
                # 过滤掉过长或过短的匹配
                if 2 <= len(name) <= 20:
                    guests.append(name)

        # 去重
        return list(dict.fromkeys(guests))

    def __str__(self) -> str:
        ep_info = f"第{self.episode_number}期" if self.episode_number else "单集"
        return f"《{self.feed_title or '未知播客'}》{ep_info}: {self.title}"


class PodcastFeed(BaseModel):
    """播客 RSS 订阅源模型."""

    title: str = Field(..., description="播客名称")
    description: str | None = Field(default=None, description="播客描述")
    url: HttpUrl | str = Field(..., description="RSS 源 URL")
    link: HttpUrl | str | None = Field(default=None, description="播客网站链接")
    language: str | None = Field(default=None, description="语言")
    last_build_date: datetime | None = Field(default=None, description="最后更新时间")
    episodes: list[PodcastEpisode] = Field(
        default_factory=list,
        description="单集列表",
    )

    def get_latest_episode(self) -> PodcastEpisode | None:
        """获取最新单集."""
        if not self.episodes:
            return None
        return max(
            self.episodes,
            key=lambda ep: ep.publish_date or datetime.min,
        )

    def __str__(self) -> str:
        return f"播客《{self.title}》({len(self.episodes)} 期)"
