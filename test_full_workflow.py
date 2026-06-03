"""完整工作流测试 — 使用已下载的音频和转录文本."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.content_processor import ContentProcessor
from core.image_generator import ImageGenerator
from models.transcript import Transcript
from models.visual_note import VisualXiaohongshuNote
from utils import configure_logging

configure_logging("DEBUG")


def main():
    """运行完整工作流."""
    print("=" * 60)
    print("完整工作流测试")
    print("=" * 60)

    # 1. 加载转录文本
    transcript_path = Path("data/transcripts/资产配置与有效前沿_transcript.md")
    if not transcript_path.exists():
        print(f"❌ 转录文件不存在: {transcript_path}")
        return

    transcript_text = transcript_path.read_text(encoding="utf-8")
    print(f"✅ 加载转录文本: {len(transcript_text)} 字符")

    # 2. 创建 Transcript 对象（模拟 RSS 解析后的数据）
    transcript = Transcript(
        episode_title="资产配置与有效前沿：去找更好的，更不一样的，更贴近时代的",
        podcast_name="面基",
        full_text=transcript_text,
        stt_provider="sensevoice",
    )
    print(f"✅ 创建 Transcript 对象")
    print(f"   播客名称: {transcript.podcast_name}")
    print(f"   单集标题: {transcript.episode_title}")

    # 3. 内容处理（使用 v7 图文模板）
    print("\n" + "-" * 60)
    print("步骤 1: 内容处理")
    print("-" * 60)

    processor = ContentProcessor()

    # 先测试纯文字生成
    print("\n[测试纯文字笔记 v5]")
    text_note = processor.process(transcript, template_name="v5")
    print(f"✅ 文字笔记生成完成")
    print(f"   标题: {text_note.title}")
    print(f"   字数: {text_note.word_count}")

    # 4. 图文生成（使用结构化内容）
    print("\n" + "-" * 60)
    print("步骤 2: 图文生成")
    print("-" * 60)

    # 手动构造结构化内容（模拟 LLM 输出）
    structured_content = {
        "hook_title": "资产配置的底层逻辑：有效前沿",
        "theme": "如何通过有效前沿理论做好资产配置",
        "introduction": "听完这期播客，我对资产配置的理解完全刷新了！原来不是拍脑门选资产，而是有数学工具的。",
        "key_points": [
            {
                "title": "资产配置不是拍脑门",
                "content": "有效前沿理论告诉我们，资产配置需要大量数据处理和计算，涉及预期收益率、波动率、相关性三个核心变量。",
                "highlight": "有效前沿理论",
                "analogy": "就像做菜不是随便抓食材，而是有配方比例的",
            },
            {
                "title": "找更好的，找更不一样的",
                "content": "资产配置的核心动作：要么找到预期收益率更高的资产，要么找到与现有资产低相关甚至负相关的资产。",
                "highlight": "低相关甚至负相关",
                "analogy": "就像篮球队不光要得分高手，还要有防守专家",
            },
            {
                "title": "组合风险不等于简单平均",
                "content": "组合的收益率是各类资产的加权平均，但组合风险受协方差矩阵影响，相关性越低，分散价值越高。",
                "highlight": "分散价值越高",
                "analogy": "就像不要把所有鸡蛋放在一个篮子里",
            },
        ],
        "quotes": [
            {"text": "资产配置的真正对象不只是资产，更是资产之间的相关性", "speaker": "韵雷"},
            {"text": "要么找到更好的资产，要么找到更不一样的资产", "speaker": "韵雷"},
        ],
        "conclusion": "原来资产配置是有数学工具的，不是凭感觉。这期让我对投资有了更科学的认知框架。",
        "tags": ["播客笔记", "资产配置", "投资", "面基", "干货分享"],
    }

    source_info = {
        "podcast_name": transcript.podcast_name,
        "episode_title": transcript.episode_title,
        "guests": "韵雷（南方基金国际业务部）",
    }

    print(f"\n结构化内容:")
    print(f"   标题: {structured_content['hook_title']}")
    print(f"   要点数: {len(structured_content['key_points'])}")
    print(f"   金句数: {len(structured_content['quotes'])}")

    # 5. 生成图片
    print("\n" + "-" * 60)
    print("步骤 3: 生成图片")
    print("-" * 60)

    import asyncio

    image_gen = ImageGenerator(output_dir=Path("data/output/images"))
    images = asyncio.run(
        image_gen.generate_note_images(
            structured_content=structured_content,
            source_info=source_info,
            style="blue",
        )
    )

    print(f"✅ 图片生成完成，共 {len(images)} 张:")
    for idx, img in enumerate(images, 1):
        print(f"   {idx}. {img.name}")

    # 6. 组装图文笔记
    print("\n" + "-" * 60)
    print("步骤 4: 组装图文笔记")
    print("-" * 60)

    visual_note = VisualXiaohongshuNote(
        text_note=text_note,
        image_paths=images,
        structured_content=structured_content,
        source_info=source_info,
        style="blue",
    )

    # 7. 输出结果
    print("\n" + "=" * 60)
    print("最终输出")
    print("=" * 60)

    print("\n【文字内容（粘贴到小红书编辑器）】\n")
    print(visual_note.format_text_for_editor())

    print("\n【图片列表（按顺序上传）】\n")
    for idx, img in enumerate(images, 1):
        print(f"  {idx}. {img}")

    # 8. 保存完整笔记
    output_path = visual_note.save_complete_note(Path("data/output"))
    print(f"\n✅ 完整笔记已保存: {output_path}")

    print("\n" + "=" * 60)
    print("🎉 工作流完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
