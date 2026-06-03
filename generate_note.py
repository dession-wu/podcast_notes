"""使用 DeepSeek 生成小红书笔记."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from core.content_processor import ContentProcessor
from services.llm_service import LLMService
from config.settings import LLMProvider
from utils import configure_logging, get_logger

configure_logging('INFO')
logger = get_logger(__name__)


def main():
    """生成小红书笔记."""
    print("=" * 60)
    print("使用 DeepSeek 生成小红书笔记")
    print("=" * 60)

    # 初始化服务
    llm_service = LLMService(provider=LLMProvider.OPENAI)
    processor = ContentProcessor(llm_service=llm_service)

    # 读取转录文本
    transcript_path = Path("./data/transcripts/面基_最新单集_transcript.txt")
    if not transcript_path.exists():
        print(f"错误: 转录文件不存在: {transcript_path}")
        return

    print(f"读取转录文本: {transcript_path}")
    transcript_text = transcript_path.read_text(encoding="utf-8")

    # 提取核心内容（前2000字作为摘要）
    summary = transcript_text[:2000]

    # 创建模拟的 Transcript 对象
    from models.transcript import Transcript, TranscriptSegment

    transcript = Transcript(
        segments=[
            TranscriptSegment(
                start_time=0.0,
                end_time=60.0,
                text=summary[:100],
            ),
        ],
        full_text=transcript_text,
        language="zh",
        duration_seconds=4577.0,
        episode_title="资产配置与有效前沿：去找更好的，更不一样的，更贴近时代的",
    )
    # 添加额外属性
    transcript.theme = "投资理财"
    transcript.key_points = [
        "资产配置的核心是找到风险和收益的平衡点",
        "有效前沿理论：在给定风险下追求最大收益",
        "分散投资可以降低非系统性风险",
        "不同资产类别的相关性影响组合效果",
        "定期再平衡是维持目标配置的关键",
    ]
    transcript.quotes = [
        "投资不是预测未来，而是管理风险",
        "不要把所有鸡蛋放在一个篮子里",
    ]

    # 测试三种模板
    templates = {
        "v4": "真人笔记型（降低AI感）",
        "v5": "知识翻译官型",
        "v6": "故事型",
    }

    for template, description in templates.items():
        print(f"\n{'='*60}")
        print(f"生成: {description} (模板 {template})")
        print(f"{'='*60}")

        try:
            note = processor.process(
                transcript=transcript,
                template_name=template,
                source_podcast="面基",
                source_episode=transcript.episode_title,
            )

            print(f"\n标题: {note.title}")
            print(f"字数: {note.word_count}")
            print(f"标签: {', '.join(note.tags)}")
            print(f"\n内容预览:")
            print("-" * 40)
            # 打印前300字
            print(note.content[:300])
            if len(note.content) > 300:
                print("...")
            print("-" * 40)

            # 检测AI标记
            ai_markers = processor._detect_ai_markers(note.content)
            if ai_markers:
                print(f"⚠️ 检测到AI标记: {', '.join(ai_markers)}")
            else:
                print("✅ 无AI标记")

            # 保存到文件
            output_path = Path(f"./data/output/note_{template}.md")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            note.save_to_file(output_path)
            print(f"\n已保存到: {output_path}")

        except Exception as e:
            print(f"❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("生成完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
