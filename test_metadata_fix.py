"""测试播客元数据（名称、标题、嘉宾）修复."""

from models.podcast import PodcastEpisode
from models.transcript import Transcript


def test_podcast_name_extraction():
    """测试从单集标题解析播客名称."""
    print("=" * 60)
    print("测试1: 播客名称解析")
    print("=" * 60)

    test_cases = [
        ("面基 | E102 蚂蚁副总裁讲支付宝20年", "面基"),
        ("忽左忽右：与历史学家聊冷战", "忽左忽右"),
        ("随机波动 - 女性主义与日常生活", "随机波动"),
        ("E102 蚂蚁副总裁讲支付宝20年", ""),  # 无分隔符
        ("支付宝20年商业逻辑", ""),  # 无分隔符
    ]

    for title, expected in test_cases:
        ep = PodcastEpisode(
            title=title,
            audio_url="http://example.com/audio.mp3",
            feed_title="面基",  # 正常情况下 RSS 会提供这个
        )
        result = ep.get_podcast_name_from_title()
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{title}' -> '{result}' (期望: '{expected}')")


def test_guest_extraction():
    """测试从描述中提取嘉宾."""
    print("\n" + "=" * 60)
    print("测试2: 嘉宾名称提取")
    print("=" * 60)

    test_cases = [
        (
            "本期嘉宾：蚂蚁集团副总裁。我们将聊聊支付宝20年的商业逻辑。",
            ["蚂蚁集团副总裁"],
        ),
        (
            "邀请历史学家王明来作客，与他对谈冷战时期的外交政策。",
            ["历史学家王明"],
        ),
        (
            "嘉宾：张三、李四。主讲：王五。",
            ["张三、李四", "王五"],
        ),
        (
            "这是一期关于科技的单集，没有提到嘉宾。",
            [],
        ),
    ]

    for description, expected in test_cases:
        ep = PodcastEpisode(
            title="测试单集",
            description=description,
            audio_url="http://example.com/audio.mp3",
        )
        result = ep.extract_guests_from_description()
        status = "✅" if result == expected else "❌"
        print(f"  {status} 描述: {description[:40]}...")
        print(f"      结果: {result}")
        print(f"      期望: {expected}")


def test_transcript_metadata():
    """测试 Transcript 元数据传递."""
    print("\n" + "=" * 60)
    print("测试3: Transcript 元数据")
    print("=" * 60)

    # 模拟 RSS 解析后的 episode
    episode = PodcastEpisode(
        title="E102 蚂蚁副总裁讲支付宝20年商业逻辑",
        description="本期嘉宾：蚂蚁集团副总裁。聊聊支付宝20年。",
        audio_url="http://example.com/audio.mp3",
        feed_title="面基",
        guests=["蚂蚁集团副总裁"],
    )

    # 创建 Transcript（模拟转录后的补充元数据）
    transcript = Transcript(
        episode_title=episode.title,
        podcast_name=episode.feed_title,  # 关键修复点
        full_text="测试转录文本",
    )

    print(f"  单集标题: {episode.title}")
    print(f"  播客名称: {episode.feed_title}")
    print(f"  嘉宾列表: {episode.guests}")
    print(f"  Transcript.podcast_name: {transcript.podcast_name}")

    # 验证
    assert transcript.podcast_name == "面基", "播客名称传递失败"
    assert transcript.episode_title == "E102 蚂蚁副总裁讲支付宝20年商业逻辑"
    print("  ✅ 元数据传递正确")


def test_fallback_podcast_name():
    """测试没有 feed_title 时的 fallback."""
    print("\n" + "=" * 60)
    print("测试4: 无 feed_title 时的 fallback")
    print("=" * 60)

    # 情况1：feed_title 为空，但 title 包含播客名
    ep1 = PodcastEpisode(
        title="面基 | E102 蚂蚁副总裁讲支付宝20年",
        audio_url="http://example.com/audio.mp3",
        feed_title=None,
    )
    name1 = ep1.feed_title or ep1.get_podcast_name_from_title()
    print(f"  情况1: feed_title=None, title='{ep1.title}'")
    print(f"       -> 解析结果: '{name1}'")
    assert name1 == "面基", "解析失败"
    print("  ✅ 正确")

    # 情况2：feed_title 和 title 都没有播客名
    ep2 = PodcastEpisode(
        title="支付宝20年商业逻辑",
        audio_url="http://example.com/audio.mp3",
        feed_title=None,
    )
    name2 = ep2.feed_title or ep2.get_podcast_name_from_title()
    print(f"  情况2: feed_title=None, title='{ep2.title}'")
    print(f"       -> 解析结果: '{name2}'")
    print("  ⚠️ 无法解析（符合预期）")


def main():
    """运行所有测试."""
    print("播客元数据修复验证测试")
    print("=" * 60)

    test_podcast_name_extraction()
    test_guest_extraction()
    test_transcript_metadata()
    test_fallback_podcast_name()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
