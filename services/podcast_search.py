"""播客搜索服务 — 多源降级策略实现.

支持的数据源（按优先级排序）：
1. PodcastIndex — 完全免费，无请求限制
2. iTunes Search — 完全免费，无请求限制
3. ListenNotes — 300次/月（备用）
4. 手动输入 RSS — 最终兜底

使用示例：
    searcher = PodcastSearcher()
    results = await searcher.search("知行小酒馆")
    # 返回标准化后的播客列表，包含 RSS 链接
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import settings
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class PodcastSearchResult:
    """标准化播客搜索结果."""

    id: str
    title: str
    description: str
    author: str
    rss_url: str
    website: str | None = None
    image_url: str | None = None
    episode_count: int | None = None
    source: str = "unknown"  # 数据来源标识


class PodcastSearchError(Exception):
    """播客搜索相关错误."""

    pass


class PodcastIndexClient:
    """PodcastIndex API 客户端.

    完全免费的播客数据库，无请求限制。
    文档: https://podcastindex-org.github.io/docs-api/
    """

    BASE_URL = "https://api.podcastindex.org/api/1.0"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        """初始化客户端.

        Args:
            api_key: API Key，默认从配置读取
            api_secret: API Secret，默认从配置读取
        """
        self.api_key = api_key or settings.podcastindex_api_key
        self.api_secret = api_secret or settings.podcastindex_api_secret

        if not self.api_key or not self.api_secret:
            raise PodcastSearchError(
                "PodcastIndex API Key 和 Secret 未配置，"
                "请在 .env 中设置 PODCASTINDEX_API_KEY 和 PODCASTINDEX_API_SECRET"
            )

    def _generate_auth_headers(self) -> dict[str, str]:
        """生成认证请求头.

        PodcastIndex 使用 SHA-1(apiKey + apiSecret + unixTime) 进行认证。
        """
        unix_time = str(int(time.time()))
        auth_string = self.api_key + self.api_secret + unix_time
        auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()

        return {
            "User-Agent": "PodcastNotesApp/1.0",
            "X-Auth-Date": unix_time,
            "X-Auth-Key": self.api_key,
            "Authorization": auth_hash,
        }

    async def search_by_term(self, term: str, max_results: int = 10) -> list[PodcastSearchResult]:
        """按关键词搜索播客.

        Args:
            term: 搜索关键词（播客名称）
            max_results: 最大返回数量

        Returns:
            标准化搜索结果列表
        """
        url = f"{self.BASE_URL}/search/byterm"
        headers = self._generate_auth_headers()
        params = {"q": term, "max": max_results}

        logger.info("PodcastIndex 搜索", term=term)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        feeds = data.get("feeds", [])
        results = []

        for feed in feeds:
            rss_url = feed.get("url", "")
            if not rss_url:
                continue

            results.append(
                PodcastSearchResult(
                    id=str(feed.get("id", "")),
                    title=feed.get("title", ""),
                    description=feed.get("description", ""),
                    author=feed.get("author", ""),
                    rss_url=rss_url,
                    website=feed.get("link"),
                    image_url=feed.get("image"),
                    episode_count=feed.get("episodeCount"),
                    source="podcastindex",
                )
            )

        logger.info("PodcastIndex 搜索完成", term=term, results=len(results))
        return results

    async def search_by_title(self, title: str, max_results: int = 10) -> list[PodcastSearchResult]:
        """按标题精准搜索播客.

        比 search_by_term 更精准，只在标题中匹配。

        Args:
            title: 播客标题
            max_results: 最大返回数量

        Returns:
            标准化搜索结果列表
        """
        url = f"{self.BASE_URL}/search/bytitle"
        headers = self._generate_auth_headers()
        params = {"q": title, "max": max_results}

        logger.info("PodcastIndex 标题搜索", title=title)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        feeds = data.get("feeds", [])
        results = []

        for feed in feeds:
            rss_url = feed.get("url", "")
            if not rss_url:
                continue

            results.append(
                PodcastSearchResult(
                    id=str(feed.get("id", "")),
                    title=feed.get("title", ""),
                    description=feed.get("description", ""),
                    author=feed.get("author", ""),
                    rss_url=rss_url,
                    website=feed.get("link"),
                    image_url=feed.get("image"),
                    episode_count=feed.get("episodeCount"),
                    source="podcastindex",
                )
            )

        logger.info("PodcastIndex 标题搜索完成", title=title, results=len(results))
        return results


class ITunesClient:
    """iTunes Search API 客户端.

    完全免费的 Apple Podcasts 搜索接口，无请求限制。
    文档: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
    """

    BASE_URL = "https://itunes.apple.com/search"

    async def search(self, term: str, max_results: int = 10) -> list[PodcastSearchResult]:
        """搜索播客.

        Args:
            term: 搜索关键词
            max_results: 最大返回数量

        Returns:
            标准化搜索结果列表（注意：iTunes 不直接返回 RSS，需要二次查询）
        """
        params = {
            "term": term,
            "media": "podcast",
            "limit": max_results,
        }

        logger.info("iTunes 搜索", term=term)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", []):
            feed_url = item.get("feedUrl", "")
            if not feed_url:
                continue

            results.append(
                PodcastSearchResult(
                    id=str(item.get("collectionId", "")),
                    title=item.get("collectionName", ""),
                    description=item.get("description", ""),
                    author=item.get("artistName", ""),
                    rss_url=feed_url,
                    website=item.get("collectionViewUrl"),
                    image_url=item.get("artworkUrl600"),
                    episode_count=item.get("trackCount"),
                    source="itunes",
                )
            )

        logger.info("iTunes 搜索完成", term=term, results=len(results))
        return results


class ListenNotesClient:
    """ListenNotes API 客户端（备用源）.

    免费额度 300次/月，作为前两个源的补充。
    文档: https://www.listennotes.com/api/docs/
    """

    BASE_URL = "https://listen-api.listennotes.com/api/v2"

    def __init__(self, api_key: str | None = None) -> None:
        """初始化客户端.

        Args:
            api_key: API Key，默认从配置读取
        """
        self.api_key = api_key or settings.listennotes_api_key

        if not self.api_key:
            raise PodcastSearchError(
                "ListenNotes API Key 未配置，"
                "请在 .env 中设置 LISTENNOTES_API_KEY"
            )

    def _get_headers(self) -> dict[str, str]:
        """生成请求头."""
        return {
            "X-ListenAPI-Key": self.api_key,
        }

    async def search(self, term: str, max_results: int = 10) -> list[PodcastSearchResult]:
        """搜索播客.

        Args:
            term: 搜索关键词
            max_results: 最大返回数量

        Returns:
            标准化搜索结果列表
        """
        url = f"{self.BASE_URL}/search"
        headers = self._get_headers()
        params = {
            "q": term,
            "type": "podcast",
            "only_in": "title,author",
            "page_size": min(max_results, 10),  # ListenNotes 每页最大10条
        }

        logger.info("ListenNotes 搜索", term=term)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", []):
            podcast = item.get("podcast", {})
            rss_url = podcast.get("rss", "")
            if not rss_url:
                continue

            results.append(
                PodcastSearchResult(
                    id=podcast.get("id", ""),
                    title=podcast.get("title_original", ""),
                    description=podcast.get("description_original", ""),
                    author=podcast.get("publisher_original", ""),
                    rss_url=rss_url,
                    website=podcast.get("website"),
                    image_url=podcast.get("image"),
                    episode_count=podcast.get("total_episodes"),
                    source="listennotes",
                )
            )

        logger.info("ListenNotes 搜索完成", term=term, results=len(results))
        return results


class PodcastSearcher:
    """播客搜索器 — 多源降级策略.

    自动按优先级尝试多个数据源，直到获取结果。

    使用示例：
        searcher = PodcastSearcher()
        results = await searcher.search("知行小酒馆")
        for podcast in results:
            print(f"{podcast.title} — {podcast.rss_url}")
    """

    def __init__(self) -> None:
        """初始化搜索器，按需加载客户端."""
        self._podcastindex: PodcastIndexClient | None = None
        self._itunes: ITunesClient | None = None
        self._listennotes: ListenNotesClient | None = None

    @property
    def podcastindex(self) -> PodcastIndexClient:
        """获取 PodcastIndex 客户端（延迟加载）."""
        if self._podcastindex is None:
            self._podcastindex = PodcastIndexClient()
        return self._podcastindex

    @property
    def itunes(self) -> ITunesClient:
        """获取 iTunes 客户端（延迟加载）."""
        if self._itunes is None:
            self._itunes = ITunesClient()
        return self._itunes

    @property
    def listennotes(self) -> ListenNotesClient | None:
        """获取 ListenNotes 客户端（延迟加载，可能返回 None）."""
        if self._listennotes is None:
            try:
                self._listennotes = ListenNotesClient()
            except PodcastSearchError:
                logger.warning("ListenNotes 未配置，跳过")
                return None
        return self._listennotes

    async def search(
        self,
        term: str,
        max_results: int = 10,
        sources: list[str] | None = None,
    ) -> list[PodcastSearchResult]:
        """搜索播客 — 多源降级.

        按优先级依次尝试各数据源，合并去重后返回。

        Args:
            term: 搜索关键词（播客名称）
            max_results: 每个数据源的最大返回数量
            sources: 指定使用的数据源列表，默认按优先级全部尝试

        Returns:
            去重后的标准化搜索结果列表

        Raises:
            PodcastSearchError: 所有数据源均搜索失败
        """
        if not term or not term.strip():
            raise PodcastSearchError("搜索关键词不能为空")

        term = term.strip()
        logger.info("开始播客搜索", term=term)

        # 定义默认搜索顺序
        default_sources = ["podcastindex", "itunes", "listennotes"]
        sources_to_try = sources or default_sources

        all_results: list[PodcastSearchResult] = []
        errors: list[str] = []

        for source in sources_to_try:
            try:
                results: list[PodcastSearchResult] = []

                if source == "podcastindex":
                    # 先尝试精准标题搜索，再尝试泛化搜索
                    results = await self.podcastindex.search_by_title(term, max_results)
                    if not results:
                        results = await self.podcastindex.search_by_term(term, max_results)

                elif source == "itunes":
                    results = await self.itunes.search(term, max_results)

                elif source == "listennotes":
                    ln_client = self.listennotes
                    if ln_client:
                        results = await ln_client.search(term, max_results)

                if results:
                    all_results.extend(results)
                    logger.info(f"数据源 {source} 返回 {len(results)} 条结果")

                    # 如果已获取足够结果，提前结束
                    if len(all_results) >= max_results:
                        break

            except Exception as e:
                error_msg = f"{source} 搜索失败: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # 去重（按 RSS URL）
        seen_rss = set()
        unique_results = []
        for result in all_results:
            if result.rss_url not in seen_rss:
                seen_rss.add(result.rss_url)
                unique_results.append(result)

        if not unique_results:
            error_detail = "; ".join(errors) if errors else "未知错误"
            raise PodcastSearchError(f"所有数据源搜索失败: {error_detail}")

        logger.info(
            "播客搜索完成",
            term=term,
            total_results=len(unique_results),
            sources_used=[r.source for r in unique_results],
        )

        return unique_results[:max_results]

    async def search_with_fallback_message(
        self,
        term: str,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """搜索播客并返回结构化结果（含降级提示）.

        适合前端展示使用，包含搜索状态和数据源信息。

        Args:
            term: 搜索关键词
            max_results: 最大返回数量

        Returns:
            结构化字典，包含 results, source_info, has_more 等字段
        """
        try:
            results = await self.search(term, max_results)
            return {
                "success": True,
                "term": term,
                "results": [
                    {
                        "id": r.id,
                        "title": r.title,
                        "description": r.description,
                        "author": r.author,
                        "rss_url": r.rss_url,
                        "website": r.website,
                        "image_url": r.image_url,
                        "episode_count": r.episode_count,
                        "source": r.source,
                    }
                    for r in results
                ],
                "count": len(results),
                "sources_used": list(set(r.source for r in results)),
            }

        except PodcastSearchError as e:
            return {
                "success": False,
                "term": term,
                "error": str(e),
                "results": [],
                "count": 0,
                "fallback_suggestion": "请尝试直接输入播客的 RSS 订阅链接",
            }
