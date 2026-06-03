"""高密度工作流测试 — 对比 v7 和 v7d 模板效果."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.content_processor import ContentProcessor
from core.image_generator import ImageGenerator
from models.transcript import Transcript
from models.visual_note import VisualXiaohongshuNote
from utils import configure_logging
import asyncio

configure_logging("INFO")


def test_dense_extraction():
    """测试高密度内容提取."""
    print("=" * 70)
    print("高密度 Prompt 测试")
    print("=" * 70)

    # 加载转录文本
    transcript_path = Path("data/transcripts/资产配置与有效前沿_transcript.md")
    transcript_text = transcript_path.read_text(encoding="utf-8")
    print(f"转录文本长度: {len(transcript_text)} 字符")

    transcript = Transcript(
        episode_title="资产配置与有效前沿：去找更好的，更不一样的，更贴近时代的",
        podcast_name="面基",
        full_text=transcript_text,
    )

    processor = ContentProcessor()

    # 测试 v7d 高密度模板
    print("\n" + "-" * 70)
    print("使用 v7d (高密度) 模板提取结构化内容...")
    print("-" * 70)

    structured = processor._extract_structured_content(
        transcript=transcript,
        cleaned_text=transcript_text[:8000],  # 8000 字输入
        key_info={
            "theme": "资产配置与有效前沿",
            "key_points": [],
            "quotes": [],
            "tags": [],
        },
    )

    print(f"\n提取结果:")
    print(f"  标题: {structured.get('hook_title', 'N/A')}")
    print(f"  主题: {structured.get('theme', 'N/A')}")
    print(f"  要点数: {len(structured.get('key_points', []))}")
    print(f"  金句数: {len(structured.get('quotes', []))}")

    # 打印每个要点的详细信息
    print(f"\n要点详情:")
    for i, point in enumerate(structured.get('key_points', []), 1):
        print(f"\n  [{i}] {point.get('title', 'N/A')}")
        print(f"      内容: {point.get('content', 'N/A')[:80]}...")
        print(f"      高亮: {point.get('highlight', 'N/A')}")
        print(f"      类比: {point.get('analogy', 'N/A')}")

    # 打印金句
    print(f"\n金句详情:")
    for i, quote in enumerate(structured.get('quotes', []), 1):
        print(f"  [{i}] \"{quote.get('text', 'N/A')}\" — {quote.get('speaker', 'N/A')}")

    return structured


def generate_dense_images(structured_content: dict):
    """生成高密度图文笔记图片."""
    print("\n" + "=" * 70)
    print("生成高密度图文笔记")
    print("=" * 70)

    source_info = {
        "podcast_name": "面基",
        "episode_title": "资产配置与有效前沿：去找更好的，更不一样的，更贴近时代的",
        "guests": "韵雷（南方基金国际业务部）",
    }

    image_gen = ImageGenerator(output_dir=Path("data/output/images_dense"))
    images = asyncio.run(
        image_gen.generate_note_images(
            structured_content=structured_content,
            source_info=source_info,
            style="blue",
        )
    )

    print(f"\n生成图片数量: {len(images)}")
    for idx, img in enumerate(images, 1):
        print(f"  {idx}. {img.name}")

    return images


def compare_density():
    """对比密度差异."""
    print("\n" + "=" * 70)
    print("密度对比分析")
    print("=" * 70)

    # 之前的 v7 输出（3个要点）
    v7_points = 3
    v7_quotes = 2
    v7_content_len = 80  # 平均每个要点80字

    # 新的 v7d 输出
    transcript_path = Path("data/transcripts/资产配置与有效前沿_transcript.md")
    transcript_text = transcript_path.read_text(encoding="utf-8")

    processor = ContentProcessor()
    transcript = Transcript(
        episode_title="资产配置与有效前沿",
        podcast_name="面基",
        full_text=transcript_text,
    )

    structured = processor._extract_structured_content(
        transcript=transcript,
        cleaned_text=transcript_text[:8000],
        key_info={"theme": "", "key_points": [], "quotes": [], "tags": []},
    )

    v7d_points = len(structured.get('key_points', []))
    v7d_quotes = len(structured.get('quotes', []))

    # 计算平均内容长度
    contents = [p.get('content', '') for p in structured.get('key_points', [])]
    avg_content_len = sum(len(c) for c in contents) / len(contents) if contents else 0

    print(f"\n对比指标:")
    print(f"  {'指标':<20} {'v7 (旧)':<10} {'v7d (新)':<10} {'提升':<10}")
    print(f"  {'-'*50}")
    print(f"  {'要点数量':<20} {v7_points:<10} {v7d_points:<10} {f'+{v7d_points-v7_points} ({(v7d_points/v7_points-1)*100:.0f}%)':<10}")
    print(f"  {'金句数量':<20} {v7_quotes:<10} {v7d_quotes:<10} {f'+{v7d_quotes-v7_quotes} ({(v7d_quotes/v7_quotes-1)*100:.0f}%)':<10}")
    print(f"  {'平均内容长度':<20} {v7_content_len:<10} {int(avg_content_len):<10} {f'+{int(avg_content_len)-v7_content_len}字':<10}")
    print(f"  {'输入文本长度':<20} {'2000字':<10} {'8000字':<10} {'+6000字':<10}")


def main():
    """运行所有测试."""
    print("高密度工作流测试")
    print("=" * 70)

    # 1. 测试高密度提取
    structured = test_dense_extraction()

    # 2. 生成图片
    images = generate_dense_images(structured)

    # 3. 对比分析
    compare_density()

    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)
    print(f"\n生成的图片保存在: data/output/images_dense/")
    print("请查看图片对比密度差异")


if __name__ == "__main__":
    main()
