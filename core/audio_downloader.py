"""音频下载模块 — 支持 RSS 订阅源解析和音频文件下载.

提供三层降级策略：
1. RSS 订阅源解析（feedparser）
2. 小宇宙网页版抓取（Playwright）
3. 本地音频文件上传
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests

from backend.config.download_settings import download_settings_manager
from config import settings
from models.podcast import PodcastEpisode, PodcastFeed
from utils import get_logger, with_retry

logger = get_logger(__name__)


class AudioDownloaderError(Exception):
    """音频下载相关错误."""

    pass


class RSSParseError(AudioDownloaderError):
    """RSS 解析错误."""

    pass


class DownloadError(AudioDownloaderError):
    """下载错误."""

    pass


class AudioDownloader:
    """音频下载器.

    支持从 RSS 订阅源解析播客信息并下载音频文件。
    """

    def __init__(self, download_dir: Path | None = None) -> None:
        """初始化下载器.

        Args:
            download_dir: 音频下载目录，默认使用配置中的目录
        """
        if download_dir:
            self.download_dir = download_dir
        else:
            ds = download_settings_manager.load()
            self.download_dir = ds.get_effective_download_dir()
        self.timeout = settings.request_timeout

    def parse_rss(self, rss_url: str) -> PodcastFeed:
        """解析 RSS 订阅源.

        Args:
            rss_url: RSS 订阅源 URL

        Returns:
            播客订阅源对象

        Raises:
            RSSParseError: RSS 解析失败
        """
        logger.info("正在解析 RSS 订阅源", url=rss_url)

        try:
            # 使用 requests 获取 RSS 内容（支持超时）
            response = requests.get(rss_url, timeout=self.timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except requests.RequestException as e:
            raise RSSParseError(f"RSS 获取失败: {e}") from e
        except Exception as e:
            raise RSSParseError(f"RSS 解析失败: {e}") from e

        if feed.bozo and feed.bozo_exception:
            logger.warning(
                "RSS 解析存在警告",
                warning=str(feed.bozo_exception),
            )

        if not feed.entries:
            raise RSSParseError("RSS 中没有找到任何单集")

        # 提取播客基本信息
        podcast_feed = PodcastFeed(
            title=feed.feed.get("title", "未知播客"),
            description=feed.feed.get("description", ""),
            url=rss_url,
            link=feed.feed.get("link", ""),
            language=feed.feed.get("language", "zh"),
        )

        # 解析单集列表
        for idx, entry in enumerate(feed.entries, 1):
            episode = self._parse_entry(entry, podcast_feed.title, rss_url)
            if episode:
                podcast_feed.episodes.append(episode)

        logger.info(
            "RSS 解析完成",
            podcast=podcast_feed.title,
            episodes=len(podcast_feed.episodes),
        )

        return podcast_feed

    def _parse_entry(
        self,
        entry: Any,
        feed_title: str,
        feed_url: str,
    ) -> PodcastEpisode | None:
        """解析 RSS 单集条目.

        Args:
            entry: feedparser 条目对象
            feed_title: 播客名称
            feed_url: RSS 源 URL

        Returns:
            播客单集对象，解析失败返回 None
        """
        # 获取音频链接
        audio_url = None

        # 优先从 enclosures 获取
        if hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("audio/"):
                    audio_url = enc.get("href", "")
                    break

        # 从 links 中查找
        if not audio_url and hasattr(entry, "links"):
            for link in entry.links:
                if link.get("type", "").startswith("audio/"):
                    audio_url = link.get("href", "")
                    break

        # 从 media_content 中查找
        if not audio_url and hasattr(entry, "media_content"):
            for media in entry.media_content:
                if media.get("type", "").startswith("audio/"):
                    audio_url = media.get("url", "")
                    break

        if not audio_url:
            logger.warning("单集缺少音频链接", title=entry.get("title", "未知"))
            return None

        # 解析发布日期
        publish_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from datetime import datetime
            publish_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            from datetime import datetime
            publish_date = datetime(*entry.updated_parsed[:6])

        # 解析时长
        duration_seconds = None
        if hasattr(entry, "itunes_duration") and entry.itunes_duration:
            duration_seconds = self._parse_duration(entry.itunes_duration)

        # 提取集数
        episode_number = None
        if hasattr(entry, "itunes_episode") and entry.itunes_episode:
            try:
                episode_number = int(entry.itunes_episode)
            except ValueError:
                pass

        # 从标题中提取集数（备用）
        if episode_number is None:
            episode_number = self._extract_episode_number(entry.get("title", ""))

        return PodcastEpisode(
            title=entry.get("title", "未知标题"),
            description=entry.get("description", ""),
            audio_url=audio_url,
            episode_number=episode_number,
            publish_date=publish_date,
            duration_seconds=duration_seconds,
            feed_title=feed_title,
            feed_url=feed_url,
        )

    @with_retry(max_attempts=3)
    def download_episode(
        self,
        episode: PodcastEpisode,
        force: bool = False,
        progress_callback: callable | None = None,
    ) -> Path:
        """下载播客单集音频.

        Args:
            episode: 播客单集对象
            force: 是否强制重新下载
            progress_callback: 进度回调函数，接收 (progress_percent, downloaded_bytes, total_bytes)

        Returns:
            本地音频文件路径

        Raises:
            DownloadError: 下载失败
        """
        # 确定保存路径
        filename = f"{episode.get_safe_filename()}.mp3"
        local_path = self.download_dir / filename

        # 检查是否已存在
        if local_path.exists() and not force:
            logger.info("音频文件已存在，跳过下载", path=str(local_path))
            episode.local_audio_path = local_path
            # 报告 100% 进度（文件已存在）
            if progress_callback:
                file_size = local_path.stat().st_size
                progress_callback(100.0, file_size, file_size)
            return local_path

        logger.info(
            "开始下载音频",
            episode=episode.title,
            url=str(episode.audio_url),
        )

        try:
            response = requests.get(
                str(episode.audio_url),
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise DownloadError(f"音频下载失败: {e}") from e

        # 获取文件大小
        total_size = int(response.headers.get("content-length", 0))
        has_known_size = total_size > 0
        logger.info(
            "音频文件大小",
            size_mb=f"{total_size / 1024 / 1024:.1f} MB" if has_known_size else "未知 (分块传输)",
        )

        # 流式下载
        downloaded = 0
        chunk_size = 8192
        last_progress = -1
        last_reported_bytes = 0
        report_interval_bytes = 256 * 1024  # 每 256KB 报告一次进度（无Content-Length时）

        try:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback:
                            if has_known_size:
                                # 有 Content-Length，按百分比报告
                                progress = min(100.0, (downloaded / total_size) * 100)
                                if int(progress) != int(last_progress):
                                    last_progress = progress
                                    progress_callback(progress, downloaded, total_size)
                            else:
                                # 无 Content-Length，按下载字节数报告（使用模拟进度）
                                # 先快速增加到 50%，然后缓慢增加到 90%，最后等待完成
                                if downloaded - last_reported_bytes >= report_interval_bytes:
                                    last_reported_bytes = downloaded
                                    # 模拟进度：基于已下载字节数估算
                                    # 假设平均播客文件约 50MB
                                    estimated_total = 50 * 1024 * 1024
                                    simulated_progress = min(90.0, (downloaded / estimated_total) * 100)
                                    # 如果下载超过 50MB，进度至少 50%
                                    if downloaded > 50 * 1024 * 1024:
                                        simulated_progress = min(90.0, 50 + (downloaded / (100 * 1024 * 1024)) * 40)
                                    progress_callback(simulated_progress, downloaded, 0)

                        # 每 10MB 记录一次进度
                        if downloaded % (10 * 1024 * 1024) < chunk_size:
                            logger.debug(
                                "下载进度",
                                downloaded_mb=f"{downloaded / 1024 / 1024:.1f} MB",
                            )
            # 下载完成后，确保报告 100%
            if progress_callback:
                if has_known_size:
                    progress_callback(100.0, downloaded, total_size)
                else:
                    progress_callback(100.0, downloaded, 0)
        except OSError as e:
            # 清理不完整文件
            if local_path.exists():
                local_path.unlink()
            raise DownloadError(f"文件写入失败: {e}") from e

        # 更新 episode 对象
        episode.local_audio_path = local_path

        logger.info(
            "音频下载完成",
            path=str(local_path),
            size_mb=f"{local_path.stat().st_size / 1024 / 1024:.1f} MB",
        )

        return local_path

    def download_from_rss(
        self,
        rss_url: str,
        episode_index: int = 0,
        progress_callback: callable | None = None,
    ) -> tuple[PodcastEpisode, Path]:
        """从 RSS 订阅源下载指定单集.

        Args:
            rss_url: RSS 订阅源 URL
            episode_index: 单集索引，0 表示最新一集，-1 表示全部

        Returns:
            (播客单集对象, 本地音频路径)

        Raises:
            AudioDownloaderError: 下载失败
        """
        # 解析 RSS
        feed = self.parse_rss(rss_url)

        if not feed.episodes:
            raise AudioDownloaderError("RSS 中没有可下载的单集")

        # 选择单集
        if episode_index == 0:
            # 获取最新单集
            episode = feed.get_latest_episode()
        elif episode_index == -1:
            raise AudioDownloaderError("批量下载请使用 download_all_from_rss 方法")
        else:
            # 按索引选择
            sorted_episodes = sorted(
                feed.episodes,
                key=lambda ep: ep.publish_date or 0,
                reverse=True,
            )
            if episode_index > len(sorted_episodes):
                raise AudioDownloaderError(
                    f"单集索引超出范围，共有 {len(sorted_episodes)} 期"
                )
            episode = sorted_episodes[episode_index - 1]

        if episode is None:
            raise AudioDownloaderError("无法获取目标单集")

        # 下载音频
        local_path = self.download_episode(episode, progress_callback=progress_callback)

        return episode, local_path

    def download_all_from_rss(
        self,
        rss_url: str,
        max_episodes: int | None = None,
    ) -> list[tuple[PodcastEpisode, Path]]:
        """从 RSS 订阅源批量下载单集.

        Args:
            rss_url: RSS 订阅源 URL
            max_episodes: 最大下载数量，None 表示全部

        Returns:
            [(播客单集对象, 本地音频路径), ...]
        """
        feed = self.parse_rss(rss_url)

        # 按发布日期排序（最新的在前）
        episodes = sorted(
            feed.episodes,
            key=lambda ep: ep.publish_date or 0,
            reverse=True,
        )

        if max_episodes:
            episodes = episodes[:max_episodes]

        results: list[tuple[PodcastEpisode, Path]] = []

        for episode in episodes:
            try:
                local_path = self.download_episode(episode)
                results.append((episode, local_path))
            except DownloadError as e:
                logger.error(
                    "单集下载失败，跳过",
                    episode=episode.title,
                    error=str(e),
                )

        logger.info(
            "批量下载完成",
            total=len(episodes),
            success=len(results),
            failed=len(episodes) - len(results),
        )

        return results

    @staticmethod
    def _parse_duration(duration_str: str) -> int | None:
        """解析时长字符串为秒数.

        支持格式：HH:MM:SS, MM:SS, 纯秒数

        Args:
            duration_str: 时长字符串

        Returns:
            秒数，解析失败返回 None
        """
        if not duration_str:
            return None

        # 尝试作为纯秒数解析
        try:
            return int(float(duration_str))
        except ValueError:
            pass

        # 解析 HH:MM:SS 或 MM:SS
        parts = duration_str.strip().split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            pass

        return None

    @staticmethod
    def _extract_episode_number(title: str) -> int | None:
        """从标题中提取集数.

        Args:
            title: 单集标题

        Returns:
            集数，提取失败返回 None
        """
        # 匹配常见格式：第123期、EP123、#123、Vol.123 等
        patterns = [
            r"第\s*(\d+)\s*[期集话]",
            r"[Ee][Pp]\s*(\d+)",
            r"#\s*(\d+)",
            r"[Vv]ol\.?\s*(\d+)",
            r"\b(\d+)\s*[期集话]",
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None

    def load_local_audio(self, file_path: str | Path) -> PodcastEpisode:
        """加载本地音频文件.

        Args:
            file_path: 本地音频文件路径

        Returns:
            播客单集对象（仅包含本地路径信息）
        """
        path = Path(file_path)

        if not path.exists():
            raise AudioDownloaderError(f"音频文件不存在: {path}")

        if not path.is_file():
            raise AudioDownloaderError(f"路径不是文件: {path}")

        # 获取文件大小
        file_size = path.stat().st_size

        episode = PodcastEpisode(
            title=path.stem,
            audio_url=str(path),
            local_audio_path=path,
        )

        logger.info(
            "加载本地音频文件",
            path=str(path),
            size_mb=f"{file_size / 1024 / 1024:.1f} MB",
        )

        return episode
