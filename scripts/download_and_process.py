"""播客转小红书主流程脚本 — V1.0 MVP.

使用方式：
    python scripts/download_and_process.py --rss <RSS_URL>
    python scripts/download_and_process.py --audio <本地音频文件路径>

示例：
    python scripts/download_and_process.py --rss https://example.com/feed.xml
    python scripts/download_and_process.py --audio ./my_podcast.mp3 --template v2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings
from core.audio_downloader import AudioDownloader, AudioDownloaderError
from core.content_processor import ContentProcessor, ContentProcessorError
from core.transcriber import Transcriber, TranscriberError
from core.xhs_publisher import publish_v9_note, XHSPublisherError
from models.podcast import PodcastEpisode
from utils import configure_logging, get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数."""
    parser = argparse.ArgumentParser(
        description="播客转小红书自动化工作流 V1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 RSS 订阅源下载最新一期并处理
  python scripts/download_and_process.py --rss https://example.com/feed.xml

  # 从 RSS 下载指定集数
  python scripts/download_and_process.py --rss https://example.com/feed.xml --episode 5

  # 处理本地音频文件
  python scripts/download_and_process.py --audio ./podcast_episode.mp3

  # 使用深度干货模板
  python scripts/download_and_process.py --rss https://example.com/feed.xml --template v2

  # 指定 LLM 提供商
  python scripts/download_and_process.py --rss https://example.com/feed.xml --llm ollama
        """,
    )

    # 输入源（互斥）
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--rss",
        type=str,
        help="RSS 订阅源 URL",
    )
    source_group.add_argument(
        "--audio",
        type=str,
        help="本地音频文件路径",
    )

    # 可选参数
    parser.add_argument(
        "--episode",
        type=int,
        default=0,
        help="单集索引（0=最新，1=最新第2期，以此类推），默认 0",
    )
    parser.add_argument(
        "--template",
        type=str,
        default="v1",
        choices=["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v7d", "v8", "v9"],
        help="小红书文案模板（v1=标准, v2=深度干货, v3=故事共鸣, v4=真人笔记, v5=知识翻译官, v6=故事型, v7=图文型, v7d=图文高密度, v8=凝练文字稿, v9=深度分析型），默认 v1",
    )
    parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "anthropic", "ollama"],
        help="LLM 提供商（覆盖配置文件设置）",
    )
    parser.add_argument(
        "--stt",
        type=str,
        choices=["whisper", "faster-whisper", "sensevoice"],
        help="STT 引擎（覆盖配置文件设置）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出目录（覆盖配置文件设置）",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="跳过下载（音频已存在时）",
    )
    parser.add_argument(
        "--skip-transcribe",
        action="store_true",
        help="跳过转录（转录文本已存在时）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细日志",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="自动发布到小红书（仅支持 v7/v7d/v8/v9 图文模板）",
    )

    return parser.parse_args()


def setup_environment(args: argparse.Namespace) -> None:
    """设置运行环境.

    Args:
        args: 命令行参数
    """
    # 配置日志
    log_level = "DEBUG" if args.verbose else settings.log_level
    configure_logging(log_level=log_level)

    # 覆盖配置
    if args.output:
        settings.data_dir = Path(args.output)
        settings.output_dir = Path(args.output) / "output"
        settings.audio_download_dir = Path(args.output) / "audio"
        settings.transcript_dir = Path(args.output) / "transcripts"

    logger.info("环境初始化完成", log_level=log_level, data_dir=str(settings.data_dir))


def step1_download_audio(args: argparse.Namespace) -> PodcastEpisode:
    """步骤 1: 获取音频文件.

    Args:
        args: 命令行参数

    Returns:
        播客单集对象
    """
    downloader = AudioDownloader()

    if args.rss:
        logger.info("步骤 1/4: 从 RSS 订阅源下载音频", rss_url=args.rss)
        episode, audio_path = downloader.download_from_rss(
            rss_url=args.rss,
            episode_index=args.episode,
        )
        logger.info("音频下载完成", path=str(audio_path))
        return episode

    elif args.audio:
        logger.info("步骤 1/4: 加载本地音频文件", path=args.audio)
        episode = downloader.load_local_audio(args.audio)
        return episode

    raise RuntimeError("未指定输入源")


def step2_transcribe_audio(episode: PodcastEpisode, args: argparse.Namespace) -> "Transcript":
    """步骤 2: 语音转文字.

    Args:
        episode: 播客单集对象
        args: 命令行参数

    Returns:
        转录文本对象
    """
    logger.info("步骤 2/4: 语音转文字", episode=episode.title)

    # 检查是否已有转录文本
    if args.skip_transcribe and episode.local_audio_path:
        transcript_path = settings.transcript_dir / f"{episode.get_safe_filename()}_transcript.md"
        if transcript_path.exists():
            logger.info("转录文本已存在，跳过", path=str(transcript_path))
            # 从文件加载转录文本（简化实现）
            from models.transcript import Transcript
            return Transcript(
                episode_title=episode.title,
                podcast_name=episode.feed_title,
                full_text=transcript_path.read_text(encoding="utf-8"),
                stt_provider="cached",
            )

    transcriber = Transcriber()

    # 检查音频文件信息
    audio_info = transcriber.check_audio_file(episode.local_audio_path)
    logger.info(
        "音频文件信息",
        duration=audio_info.get("duration_formatted", "未知"),
        size_mb=audio_info.get("size_mb", "未知"),
    )

    # 执行转录
    transcript = transcriber.transcribe(episode, language="zh")

    logger.info(
        "语音转文字完成",
        word_count=transcript.word_count,
        segments=transcript.segment_count,
    )

    return transcript


def step3_generate_note(
    transcript: "Transcript",
    args: argparse.Namespace,
) -> "XiaohongshuNote":
    """步骤 3: 生成小红书笔记.

    Args:
        transcript: 转录文本对象
        args: 命令行参数

    Returns:
        小红书笔记对象
    """
    logger.info("步骤 3/4: 生成小红书笔记")

    # 初始化 LLM 服务
    from config.settings import LLMProvider
    from services.llm_service import LLMService

    llm_provider = None
    if args.llm:
        llm_provider = LLMProvider(args.llm)

    llm_service = LLMService(provider=llm_provider)
    processor = ContentProcessor(llm_service=llm_service)

    # 准备额外参数（播客来源信息）
    process_kwargs = {}

    # 尝试从 episode 中提取嘉宾信息
    if hasattr(episode, 'guests') and episode.guests:
        process_kwargs["guests"] = ", ".join(episode.guests)
    elif hasattr(episode, 'extract_guests_from_description'):
        extracted_guests = episode.extract_guests_from_description()
        if extracted_guests:
            process_kwargs["guests"] = ", ".join(extracted_guests)

    # 生成笔记
    # v7/v8/v9 是图文模板，需要特殊处理
    visual_templates = ("v7", "v7d", "v8", "v9")
    if args.template in visual_templates:
        # 图文模板：先获取别名，process方法会自动处理
        process_kwargs["template_alias"] = args.template
        template_name = f"xiaohongshu_note_{args.template}"
    else:
        template_name = f"xiaohongshu_note_{args.template}"

    note = processor.process(transcript, template_name=template_name, **process_kwargs)

    logger.info(
        "小红书笔记生成完成",
        title=note.title if hasattr(note, 'title') else "图文笔记",
        word_count=note.word_count if hasattr(note, 'word_count') else 0,
        tags=note.tags if hasattr(note, 'tags') else [],
    )

    return note


def step4_output_result(
    note: "XiaohongshuNote" | "VisualXiaohongshuNote",
    args: argparse.Namespace,
    structured_content: dict | None = None,
) -> None:
    """步骤 4: 输出结果.

    Args:
        note: 小红书笔记对象（纯文字或图文）
        args: 命令行参数
        structured_content: v9 结构化内容（发布时需要）
    """
    from models.visual_note import VisualXiaohongshuNote

    logger.info("步骤 4/4: 输出结果")

    is_visual = isinstance(note, VisualXiaohongshuNote)

    # 打印到终端
    print("\n" + "=" * 60)
    if is_visual:
        print("📝 小红书图文笔记已生成")
    else:
        print("📝 小红书笔记已生成")
    print("=" * 60)

    if is_visual:
        # 图文笔记输出
        print("\n【文字内容（粘贴到小红书编辑器）】\n")
        print(note.format_text_for_editor())
        print("\n【图片列表（按顺序上传）】\n")
        for idx, img_path in enumerate(note.image_paths, 1):
            print(f"  {idx}. {img_path}")
    else:
        # 纯文字笔记输出
        print(note.format_full_text())

    print("=" * 60)

    # 显示文件路径
    if is_visual:
        safe_title = "".join(
            c for c in note.text_note.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:30]
    else:
        safe_title = "".join(
            c for c in note.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:30]

    output_path = settings.output_dir / f"{safe_title}_xiaohongshu.md"

    print(f"\n📁 笔记已保存至: {output_path}")

    # 自动发布到小红书
    if args.publish and is_visual and args.template in ("v7", "v7d", "v8", "v9"):
        print("\n🚀 正在自动发布到小红书...")
        try:
            # 获取图片路径
            image_paths = note.image_paths

            # 获取结构化内容（v9 需要）
            content_for_publish = structured_content
            if not content_for_publish and hasattr(note, 'structured_content'):
                content_for_publish = note.structured_content

            # 发布
            result = publish_v9_note(
                structured_content=content_for_publish,
                image_paths=image_paths,
            )

            if result.get("success"):
                print(f"\n✅ 发布成功！")
                print(f"   笔记ID: {result.get('note_id', '未知')}")
                print(f"   标题: {result.get('title', '未知')}")
            else:
                print(f"\n❌ 发布失败: {result.get('error', '未知错误')}")

        except XHSPublisherError as e:
            print(f"\n❌ 发布失败: {e}")
            logger.error("小红书发布失败", error=str(e))
        except Exception as e:
            print(f"\n❌ 发布时出错: {e}")
            logger.exception("发布时未预期的错误")
    else:
        print("\n💡 下一步操作:")
        if is_visual:
            print("   1. 复制上方文字到小红书编辑器")
            print("   2. 按顺序上传图片列表中的图片")
            print("   3. 添加话题标签")
            print("   4. 点击发布！")
        else:
            print("   1. 复制上方文案到小红书创作者中心")
            print("   2. 配一张与主题相关的封面图")
            print("   3. 添加 3-5 个话题标签")
            print("   4. 点击发布！")


def main() -> int:
    """主入口函数.

    Returns:
        退出码（0=成功，1=失败）
    """
    args = parse_args()
    setup_environment(args)

    logger.info("=" * 60)
    logger.info("播客转小红书自动化工作流 V1.0 启动")
    logger.info("=" * 60)

    try:
        # 步骤 1: 获取音频
        episode = step1_download_audio(args)

        # 步骤 2: 语音转文字
        transcript = step2_transcribe_audio(episode, args)

        # 步骤 3: 生成小红书笔记
        note = step3_generate_note(transcript, args)

        # 获取结构化内容（用于发布）
        structured_content = None
        if hasattr(note, 'structured_content'):
            structured_content = note.structured_content
        elif hasattr(note, 'text_note') and hasattr(note.text_note, 'structured_content'):
            structured_content = note.text_note.structured_content

        # 步骤 4: 输出结果
        step4_output_result(note, args, structured_content)

        logger.info("=" * 60)
        logger.info("工作流执行完成！")
        logger.info("=" * 60)

        return 0

    except AudioDownloaderError as e:
        logger.error("音频下载失败", error=str(e))
        print(f"\n❌ 音频下载失败: {e}", file=sys.stderr)
        return 1

    except TranscriberError as e:
        logger.error("语音转文字失败", error=str(e))
        print(f"\n❌ 语音转文字失败: {e}", file=sys.stderr)
        return 1

    except ContentProcessorError as e:
        logger.error("内容处理失败", error=str(e))
        print(f"\n❌ 内容处理失败: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        logger.info("用户中断执行")
        print("\n⚠️ 已中断", file=sys.stderr)
        return 130

    except Exception as e:
        logger.exception("未预期的错误")
        print(f"\n💥 未预期的错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
