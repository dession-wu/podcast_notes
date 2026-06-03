#!/usr/bin/env python3
"""播客搜索功能测试脚本."""

import asyncio

from services.podcast_search import ITunesClient, PodcastSearcher


async def test_itunes():
    """测试 iTunes 搜索."""
    print("=" * 60)
    print("测试 iTunes 搜索")
    print("=" * 60)

    client = ITunesClient()
    results = await client.search("知行小酒馆", max_results=5)

    print(f"找到 {len(results)} 个结果:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}")
        print(f"   作者: {r.author}")
        print(f"   RSS: {r.rss_url}")
        print(f"   集数: {r.episode_count}")
        print()


async def test_podcastindex():
    """测试 PodcastIndex 搜索."""
    print("=" * 60)
    print("测试 PodcastIndex 搜索")
    print("=" * 60)

    try:
        from services.podcast_search import PodcastIndexClient

        client = PodcastIndexClient()
        results = await client.search_by_term("知行小酒馆", max_results=5)

        print(f"找到 {len(results)} 个结果:\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            print(f"   作者: {r.author}")
            print(f"   RSS: {r.rss_url}")
            print(f"   集数: {r.episode_count}")
            print()
    except Exception as e:
        print(f"PodcastIndex 测试失败: {e}")
        print("请检查 PODCASTINDEX_API_KEY 和 PODCASTINDEX_API_SECRET 是否配置正确")


async def test_multi_source():
    """测试多源降级搜索."""
    print("=" * 60)
    print("测试多源降级搜索 (PodcastSearcher)")
    print("=" * 60)

    searcher = PodcastSearcher()

    # 测试搜索
    term = "知行小酒馆"
    print(f"搜索关键词: {term}\n")

    try:
        results = await searcher.search(term, max_results=5)
        print(f"找到 {len(results)} 个去重结果:\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            print(f"   作者: {r.author}")
            print(f"   RSS: {r.rss_url}")
            print(f"   来源: {r.source}")
            print()
    except Exception as e:
        print(f"搜索失败: {e}")

    # 测试结构化返回
    print("\n测试结构化返回:\n")
    result = await searcher.search_with_fallback_message("忽左忽右", max_results=3)
    print(f"成功: {result['success']}")
    print(f"结果数: {result['count']}")
    if result['success']:
        print(f"使用的数据源: {result['sources_used']}")


async def main():
    """运行所有测试."""
    print("播客搜索功能测试\n")

    # 测试 iTunes（无需认证）
    await test_itunes()

    # 测试 PodcastIndex（需要配置）
    await test_podcastindex()

    # 测试多源搜索
    await test_multi_source()

    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
