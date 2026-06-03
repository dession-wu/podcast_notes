"""测试 v8 播客凝练版文字稿模板."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
from core.image_generator import ImageGenerator
from utils import configure_logging

configure_logging("INFO")


def test_transcript_template():
    """测试新文字稿模板渲染."""
    print("=" * 70)
    print("测试 v8 播客凝练版文字稿模板")
    print("=" * 70)

    # 模拟 v8 结构化内容（按章节结构）
    structured_content = {
        "hook_title": "资产配置的底层逻辑",
        "theme": "如何通过有效前沿理论做好资产配置",
        "introduction": "听完这期播客，我对资产配置的理解完全刷新了！",
        "sections": [
            {
                "section_title": "一、什么是有效前沿",
                "subsections": [
                    {
                        "subtitle": "有效前沿的定义",
                        "points": [
                            {"text": "有效前沿是风险和收益坐标系中的最佳曲线", "highlight": "最佳曲线"},
                            {"text": "在同样风险下，曲线上的组合收益最高"},
                            {"text": "在同样收益下，曲线上的组合风险最低"},
                        ]
                    },
                    {
                        "subtitle": "实际意义",
                        "points": [
                            {"text": "曲线以下的组合都是性价比低的垃圾组合", "highlight": "性价比低"},
                            {"text": "投资者应该追求曲线上的配置方案"},
                        ]
                    }
                ]
            },
            {
                "section_title": "二、如何找到更好的资产",
                "subsections": [
                    {
                        "subtitle": "两个核心动作",
                        "points": [
                            {"text": "找到预期收益率更高的资产", "highlight": "预期收益率更高"},
                            {"text": "找到与现有资产低相关甚至负相关的资产", "highlight": "低相关甚至负相关"},
                        ]
                    },
                    {
                        "subtitle": "关键认知",
                        "points": [
                            {"text": "资产配置的真正对象不只是资产，更是资产之间的相关性", "highlight": "资产之间的相关性"},
                            {"text": "要么找到更好的资产，要么找到更不一样的资产"},
                        ]
                    }
                ]
            },
            {
                "section_title": "三、组合风险的本质",
                "subsections": [
                    {
                        "subtitle": "风险计算方式",
                        "points": [
                            {"text": "组合收益率是各类资产的加权平均", "highlight": "加权平均"},
                            {"text": "组合风险受协方差矩阵影响，不是简单平均", "highlight": "协方差矩阵"},
                            {"text": "相关性越低，分散价值越高"},
                        ]
                    }
                ]
            }
        ],
        "conclusion": "原来资产配置是有数学工具的，不是凭感觉。",
        "tags": ["播客笔记", "资产配置", "投资", "面基", "干货分享"],
    }

    source_info = {
        "podcast_name": "面基",
        "episode_title": "资产配置与有效前沿",
        "guests": "韵雷（南方基金国际业务部）",
    }

    print(f"\n结构化内容:")
    print(f"  章节数: {len(structured_content['sections'])}")
    for i, section in enumerate(structured_content['sections'], 1):
        print(f"  章节 {i}: {section['section_title']}")
        print(f"    子话题数: {len(section['subsections'])}")
        for j, sub in enumerate(section['subsections'], 1):
            print(f"    子话题 {j}: {sub['subtitle']} ({len(sub['points'])} 条论述)")

    # 生成图片
    print("\n" + "-" * 70)
    print("生成图片...")
    print("-" * 70)

    image_gen = ImageGenerator(output_dir=Path("data/output/images_v8"))
    images = asyncio.run(
        image_gen.generate_note_images(
            structured_content=structured_content,
            source_info=source_info,
            style="blue",
        )
    )

    print(f"\n✅ 生成完成，共 {len(images)} 张图片:")
    for idx, img in enumerate(images, 1):
        print(f"  {idx}. {img.name}")

    return images


def main():
    """运行测试."""
    print("v8 播客凝练版文字稿测试")
    print("=" * 70)

    images = test_transcript_template()

    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)
    print(f"\n图片保存在: data/output/images_v8/")


if __name__ == "__main__":
    main()
