"""测试图文工作流端到端流程."""

import asyncio
from pathlib import Path

from core.content_processor import ContentProcessor
from core.image_generator import ImageGenerator
from models.transcript import Transcript
from models.visual_note import VisualXiaohongshuNote


# 模拟播客转录内容（基于面基播客支付宝主题）
SAMPLE_TRANSCRIPT = """
主播：欢迎收听面基，我是主播。今天我们有幸请到了蚂蚁集团的一位副总裁，来聊聊支付宝这20年的商业逻辑。

嘉宾：大家好。支付宝到今年正好20年，很多人可能不知道，支付宝的诞生其实是个意外。2003年淘宝成立，但当时的网购最大的问题是信任。买家怕付了钱收不到货，卖家怕发了货收不到钱。

主播：所以支付宝最初就是为了解决这个问题？

嘉宾：对，2004年支付宝正式上线，最初就是一个担保交易工具。买家先把钱打到支付宝，确认收货后支付宝再打给卖家。这个模式现在看来很平常，但在当时是非常创新的。

主播：那后来是怎么从淘宝的一个工具，变成独立平台的？

嘉宾：这是一个渐进的过程。2008年左右，我们开始意识到，支付宝不应该只是服务淘宝，它可以服务整个社会。比如水电煤缴费、信用卡还款，这些场景跟淘宝没关系，但用户需要。

主播：我记得2013年余额宝的推出是一个重要节点？

嘉宾：是的，余额宝可以说是支付宝从支付工具向金融平台转型的标志性事件。我们把货币基金和支付账户打通，让用户的钱不仅能花，还能生息。这个创新推动了整个货币基金互联网化的浪潮。

主播：但也引发了一些监管的关注？

嘉宾：任何创新都会伴随监管的跟进，这是正常的。支付宝的发展史，某种程度上就是一部创新与监管博弈的历史。但我们始终认为，合规是底线，创新要在合规的框架内进行。

主播：现在支付宝的定位是什么？

嘉宾：我们希望成为数字生活开放平台。不仅仅是支付，还包括出行、医疗、政务等各个生活场景。支付宝最大的成功，可能是让用户忘记了它的存在——它就像水电煤一样，变成了基础设施。

主播：最后想问问，对于普通用户理解支付宝，你有什么建议？

嘉宾：我想引用一句话：支付宝不是在做金融，而是在做信任。从最早的担保交易，到现在的芝麻信用，核心都是解决信任问题。理解了这一点，就理解了支付宝的底层逻辑。
"""


def test_structured_extraction():
    """测试结构化内容提取."""
    print("=" * 60)
    print("测试1: 结构化内容提取")
    print("=" * 60)

    processor = ContentProcessor()

    transcript = Transcript(
        podcast_name="面基",
        episode_title="E102 蚂蚁副总裁讲支付宝20年商业逻辑",
        text=SAMPLE_TRANSCRIPT,
    )

    # 测试文本预处理
    cleaned = processor._preprocess_text(transcript.text)
    print(f"清洗后文本长度: {len(cleaned)} 字符")

    # 测试关键信息提取
    key_info = processor._extract_key_info(cleaned)
    print(f"\n提取的主题: {key_info.get('theme', 'N/A')}")
    print(f"核心要点数: {len(key_info.get('key_points', []))}")
    print(f"金句数: {len(key_info.get('quotes', []))}")
    print(f"标签: {key_info.get('tags', [])}")

    # 测试结构化内容提取
    structured = processor._extract_structured_content(
        transcript=transcript,
        cleaned_text=cleaned,
        key_info=key_info,
    )

    print(f"\n结构化内容:")
    print(f"  标题: {structured.get('hook_title', 'N/A')}")
    print(f"  主题: {structured.get('theme', 'N/A')}")
    print(f"  引言: {structured.get('introduction', 'N/A')[:50]}...")
    print(f"  要点数: {len(structured.get('key_points', []))}")
    print(f"  金句数: {len(structured.get('quotes', []))}")
    print(f"  标签: {structured.get('tags', [])}")

    return structured


def test_image_generation(structured_content: dict):
    """测试图片生成."""
    print("\n" + "=" * 60)
    print("测试2: 图片生成")
    print("=" * 60)

    source_info = {
        "podcast_name": "面基",
        "episode_title": "E102 蚂蚁副总裁讲支付宝20年",
        "guests": "蚂蚁集团副总裁",
    }

    gen = ImageGenerator(output_dir=Path("data/output/images"))

    images = asyncio.run(
        gen.generate_note_images(
            structured_content=structured_content,
            source_info=source_info,
            style="blue",
        )
    )

    print(f"生成图片数量: {len(images)}")
    for img in images:
        print(f"  - {img.name}")

    return images


def test_visual_note_save():
    """测试图文笔记保存."""
    print("\n" + "=" * 60)
    print("测试3: 图文笔记保存")
    print("=" * 60)

    from models.xiaohongshu import XiaohongshuNote

    text_note = XiaohongshuNote(
        title="支付宝20年商业逻辑",
        content="测试内容",
        tags=["播客笔记", "支付宝", "商业思维"],
        source_podcast="面基",
        source_episode="E102",
    )

    visual_note = VisualXiaohongshuNote(
        text_note=text_note,
        image_paths=[
            Path("data/output/images/cover_test.png"),
            Path("data/output/images/content_01.png"),
            Path("data/output/images/summary.png"),
        ],
        structured_content={
            "introduction": "听完这期播客，我对支付宝的理解完全刷新了！",
            "conclusion": "从支付工具到金融基础设施，这个认知升级很有意思。",
            "tags": ["播客笔记", "支付宝", "商业思维", "面基", "干货分享"],
        },
        source_info={
            "podcast_name": "面基",
            "episode_title": "E102",
        },
    )

    # 测试文字格式化
    editor_text = visual_note.format_text_for_editor()
    print("编辑器文字内容:")
    print(editor_text)
    print()

    # 测试保存
    output_path = visual_note.save_complete_note(Path("data/output"))
    print(f"笔记已保存到: {output_path}")


def test_full_workflow():
    """测试完整工作流."""
    print("\n" + "=" * 60)
    print("测试4: 完整工作流（使用 v7 模板）")
    print("=" * 60)

    processor = ContentProcessor()

    transcript = Transcript(
        podcast_name="面基",
        episode_title="E102 蚂蚁副总裁讲支付宝20年商业逻辑",
        text=SAMPLE_TRANSCRIPT,
    )

    try:
        result = processor.process(
            transcript=transcript,
            template_name="v7",
            guests="蚂蚁集团副总裁",
            style="blue",
        )

        if isinstance(result, VisualXiaohongshuNote):
            print(f"生成图文笔记成功！")
            print(f"  标题: {result.text_note.title}")
            print(f"  图片数: {len(result.image_paths)}")
            print(f"  配色: {result.style}")
            print(f"\n编辑器文字:")
            print(result.format_text_for_editor())
        else:
            print(f"生成纯文字笔记: {result.title}")

    except Exception as e:
        print(f"工作流测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """运行所有测试."""
    print("小红书图文工作流端到端测试")
    print("=" * 60)

    # 测试1: 结构化提取
    structured = test_structured_extraction()

    # 测试2: 图片生成
    images = test_image_generation(structured)

    # 测试3: 笔记保存
    test_visual_note_save()

    # 测试4: 完整工作流（可选，需要LLM）
    # test_full_workflow()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
