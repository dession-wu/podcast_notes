"""Episodes router for podcast episode listing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import socket
from urllib.error import URLError

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.audio_downloader import AudioDownloader, RSSParseError
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


class EpisodeItem(BaseModel):
    """单集列表项模型."""

    index: int                    # 在列表中的序号（用于下载）
    title: str
    description: str | None = None
    duration_seconds: int | None = None
    duration_formatted: str | None = None
    publish_date: str | None = None  # ISO 格式日期字符串
    episode_number: int | None = None
    audio_url: str | None = None


class EpisodesResponse(BaseModel):
    """集数列表响应模型."""

    podcast_title: str
    podcast_description: str | None = None
    podcast_image: str | None = None
    total_episodes: int
    episodes: list[EpisodeItem]


class EpisodesRequest(BaseModel):
    """集数列表请求模型."""

    rss_url: str
    sort: str = "newest"  # "newest" | "oldest"
    page: int = 1
    page_size: int = 20


def _format_duration(seconds: int | None) -> str | None:
    """格式化秒数为可读字符串."""
    if not seconds:
        return None
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


@router.post("/", response_model=EpisodesResponse)
async def get_episodes(request: EpisodesRequest):
    """获取播客单集列表.

    通过 RSS URL 解析获取播客的所有单集信息。

    Args:
        request: 包含 RSS URL、排序方式和分页参数

    Returns:
        播客信息和单集列表
    """
    try:
        # 设置全局 socket 超时（feedparser 内部使用 urllib）
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(15)

        try:
            downloader = AudioDownloader()
            feed = downloader.parse_rss(request.rss_url)
        except (RSSParseError, URLError, socket.timeout, OSError) as e:
            logger.warning("RSS 解析失败", error=str(e), rss_url=request.rss_url)
            return EpisodesResponse(
                podcast_title="未知播客",
                podcast_description="无法解析该播客的 RSS 订阅源，可能是网络连接问题或 RSS 地址无效。",
                podcast_image=None,
                total_episodes=0,
                episodes=[],
            )
        finally:
            socket.setdefaulttimeout(old_timeout)

        # 排序
        episodes = feed.episodes
        if request.sort == "newest":
            episodes = sorted(
                episodes,
                key=lambda ep: ep.publish_date or datetime.min,
                reverse=True,
            )
        elif request.sort == "oldest":
            episodes = sorted(
                episodes,
                key=lambda ep: ep.publish_date or datetime.max,
                reverse=False,
            )

        total = len(episodes)

        # 分页
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        paged_episodes = episodes[start:end]

        # 构建响应
        episode_items = []
        for idx, ep in enumerate(paged_episodes, start=start + 1):
            desc = ep.description
            if desc and len(desc) > 200:
                desc = desc[:200] + "..."
            episode_items.append(
                EpisodeItem(
                    index=idx,
                    title=ep.title,
                    description=desc,
                    duration_seconds=ep.duration_seconds,
                    duration_formatted=_format_duration(ep.duration_seconds),
                    publish_date=ep.publish_date.isoformat() if ep.publish_date else None,
                    episode_number=ep.episode_number,
                    audio_url=str(ep.audio_url) if ep.audio_url else None,
                )
            )

        return EpisodesResponse(
            podcast_title=feed.title,
            podcast_description=feed.description,
            podcast_image=None,
            total_episodes=total,
            episodes=episode_items,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取集数列表失败", error=str(e), rss_url=request.rss_url)
        raise HTTPException(status_code=500, detail=f"获取集数列表失败: {str(e)}")
