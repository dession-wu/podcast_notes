"""测试图片生成器."""

import asyncio
from pathlib import Path

from core.image_generator import ImageGenerator


async def test_cover():
    """测试封面生成."""
    gen = ImageGenerator(output_dir=Path("data/output/images"))

    # 测试蓝色主题
    cover_blue = await gen.generate_cover(
        title="支付宝20年商业逻辑",
        podcast_name="面基",
        episode_title="E102 蚂蚁副总裁讲支付宝",
        guests="蚂蚁集团副总裁",
        style="blue",
    )
    print(f"封面(蓝)生成: {cover_blue}")

    # 测试绿色主题
    cover_green = await gen.generate_cover(
        title="支付宝20年商业逻辑",
        podcast_name="面基",
        episode_title="E102 蚂蚁副总裁讲支付宝",
        guests="蚂蚁集团副总裁",
        style="green",
    )
    print(f"封面(绿)生成: {cover_green}")

    # 测试紫色主题
    cover_purple = await gen.generate_cover(
        title="支付宝20年商业逻辑",
        podcast_name="面基",
        episode_title="E102 蚂蚁副总裁讲支付宝",
        guests="蚂蚁集团副总裁",
        style="purple",
    )
    print(f"封面(紫)生成: {cover_purple}")


async def test_content_page():
    """测试内容页生成."""
    gen = ImageGenerator(output_dir=Path("data/output/images"))

    key_points = [
        {
            "title": "支付宝的诞生是个意外",
            "content": "2004年支付宝最初只是淘宝的担保交易工具，为了解决网购信任问题。",
            "highlight": "担保交易模式",
            "analogy": "就像你和朋友之间有个共同信任的中间人，确保买卖双方都放心",
        },
        {
            "title": "从工具到平台的跃迁",
            "content": "支付宝逐渐独立，从服务淘宝扩展到服务整个社会，成为基础设施。",
            "highlight": "成为基础设施",
            "analogy": "就像水电煤一样，变成了生活中离不开的基础服务",
        },
    ]

    quotes = [
        {"text": "支付宝最大的成功，是让用户忘记了它的存在", "speaker": "蚂蚁副总裁"},
    ]

    source_info = {
        "podcast_name": "面基",
        "episode_title": "E102 蚂蚁副总裁讲支付宝",
    }

    page = await gen.generate_content_page(
        page_num=1,
        section_title="核心观点",
        key_points=key_points,
        quotes=quotes,
        source_info=source_info,
        style="blue",
    )
    print(f"内容页生成: {page}")


async def test_summary_page():
    """测试总结页生成."""
    gen = ImageGenerator(output_dir=Path("data/output/images"))

    key_points = [
        "支付宝诞生于解决网购信任问题",
        "从淘宝工具成长为社会基础设施",
        "技术创新与监管博弈并行",
        "全球化是下一阶段核心战略",
    ]

    source_info = {
        "podcast_name": "面基",
        "episode_title": "E102 蚂蚁副总裁讲支付宝",
        "guests": "蚂蚁集团副总裁",
    }

    summary = await gen.generate_summary_page(
        key_points=key_points,
        source_info=source_info,
        conclusion="听完这期，我对支付宝的理解从'支付工具'升级到了'金融基础设施'，这种认知跃迁很有意思。",
        style="blue",
    )
    print(f"总结页生成: {summary}")


async def test_full_note():
    """测试完整笔记生成."""
    gen = ImageGenerator(output_dir=Path("data/output/images"))

    structured_content = {
        "hook_title": "支付宝20年商业逻辑",
        "key_points": [
            {
                "title": "支付宝的诞生是个意外",
                "content": "2004年支付宝最初只是淘宝的担保交易工具，为了解决网购信任问题。",
                "highlight": "担保交易模式",
                "analogy": "就像你和朋友之间有个共同信任的中间人",
            },
            {
                "title": "从工具到平台的跃迁",
                "content": "支付宝逐渐独立，从服务淘宝扩展到服务整个社会，成为基础设施。",
                "highlight": "成为基础设施",
                "analogy": "就像水电煤一样，变成了生活中离不开的基础服务",
            },
            {
                "title": "技术创新与监管博弈",
                "content": "余额宝的诞生推动了货币基金互联网化，也引发了监管关注。",
                "highlight": "推动货币基金互联网化",
                "analogy": "就像把银行柜台搬到了手机上",
            },
        ],
        "quotes": [
            {"text": "支付宝最大的成功，是让用户忘记了它的存在", "speaker": "蚂蚁副总裁"},
            {"text": "我们不是在做金融，而是在做信任", "speaker": "蚂蚁副总裁"},
        ],
        "conclusion": "听完这期，我对支付宝的理解从'支付工具'升级到了'金融基础设施'。",
    }

    source_info = {
        "podcast_name": "面基",
        "episode_title": "E102 蚂蚁副总裁讲支付宝20年",
        "guests": "蚂蚁集团副总裁",
    }

    images = await gen.generate_note_images(
        structured_content=structured_content,
        source_info=source_info,
        style="blue",
    )
    print(f"完整笔记生成完成，共 {len(images)} 张图片:")
    for img in images:
        print(f"  - {img}")


async def main():
    """运行所有测试."""
    print("=" * 50)
    print("测试封面生成")
    print("=" * 50)
    await test_cover()

    print("\n" + "=" * 50)
    print("测试内容页生成")
    print("=" * 50)
    await test_content_page()

    print("\n" + "=" * 50)
    print("测试总结页生成")
    print("=" * 50)
    await test_summary_page()

    print("\n" + "=" * 50)
    print("测试完整笔记生成")
    print("=" * 50)
    await test_full_note()

    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
