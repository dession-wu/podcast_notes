"""HTML截图图片生成器 — 将结构化内容渲染为小红书竖图.

使用 Playwright 将 HTML 模板渲染为 PNG 图片，支持封面、内容页、总结页三种模板。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

from config import settings
from utils import get_logger

logger = get_logger(__name__)


class ImageGeneratorError(Exception):
    """图片生成相关错误."""

    pass


class ImageGenerator:
    """HTML截图图片生成器.

    将结构化播客内容渲染为小红书格式的竖版图片。
    """

    # 小红书竖图标准尺寸
    PAGE_WIDTH = 900
    PAGE_HEIGHT = 1200
    # 高清渲染倍率
    DEVICE_SCALE = 2

    # 配色方案
    COLOR_SCHEMES = {
        "blue": {
            "primary": "#1a365d",
            "secondary": "#2c5282",
            "accent": "#ed8936",
            "bg": "#f7fafc",
            "text": "#2d3748",
            "light_text": "#718096",
            "highlight_bg": "#fef3c7",
        },
        "green": {
            "primary": "#22543d",
            "secondary": "#276749",
            "accent": "#d69e2e",
            "bg": "#f0fff4",
            "text": "#2d3748",
            "light_text": "#718096",
            "highlight_bg": "#fef3c7",
        },
        "purple": {
            "primary": "#44337a",
            "secondary": "#553c9a",
            "accent": "#b83280",
            "bg": "#faf5ff",
            "text": "#2d3748",
            "light_text": "#718096",
            "highlight_bg": "#fef3c7",
        },
    }

    def __init__(self, output_dir: Path | None = None) -> None:
        """初始化图片生成器.

        Args:
            output_dir: 图片输出目录，默认使用 data/output/images
        """
        self.output_dir = output_dir or (settings.output_dir / "images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 模板环境
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
        )

        logger.info("图片生成器初始化完成", output_dir=str(self.output_dir))

    async def generate_cover(
        self,
        title: str,
        podcast_name: str,
        episode_title: str,
        guests: str | None = None,
        style: str = "blue",
    ) -> Path:
        """生成封面图.

        Args:
            title: 主标题（钩子）
            podcast_name: 播客名称
            episode_title: 单集标题
            guests: 嘉宾名称
            style: 配色方案 (blue/green/purple)

        Returns:
            生成的图片路径
        """
        colors = self.COLOR_SCHEMES.get(style, self.COLOR_SCHEMES["blue"])

        html_content = self._render_template(
            "cover.html",
            {
                "title": title,
                "podcast_name": podcast_name,
                "episode_title": episode_title,
                "guests": guests or "",
                "colors": colors,
                "page_width": self.PAGE_WIDTH,
                "page_height": self.PAGE_HEIGHT,
            },
        )

        output_path = self.output_dir / f"cover_{self._safe_filename(title)}.png"
        await self._html_to_image(html_content, output_path)

        logger.info("封面图生成完成", path=str(output_path))
        return output_path

    async def generate_content_page(
        self,
        page_num: int,
        section_title: str,
        key_points: list[dict[str, str]],
        quotes: list[dict[str, str]] | None = None,
        source_info: dict[str, str] | None = None,
        style: str = "blue",
    ) -> Path:
        """生成内容页.

        Args:
            page_num: 页码
            section_title: 章节标题
            key_points: 要点列表，每项包含 title, content, highlight, analogy
            quotes: 金句列表，每项包含 text, speaker
            source_info: 来源信息，包含 podcast_name, episode_title
            style: 配色方案

        Returns:
            生成的图片路径
        """
        colors = self.COLOR_SCHEMES.get(style, self.COLOR_SCHEMES["blue"])

        html_content = self._render_template(
            "content.html",
            {
                "page_num": page_num,
                "section_title": section_title,
                "key_points": key_points,
                "quotes": quotes or [],
                "source_info": source_info or {},
                "colors": colors,
                "page_width": self.PAGE_WIDTH,
                "page_height": self.PAGE_HEIGHT,
            },
        )

        output_path = self.output_dir / f"content_{page_num:02d}.png"
        await self._html_to_image(html_content, output_path)

        logger.info("内容页生成完成", page=page_num, path=str(output_path))
        return output_path

    async def generate_summary_page(
        self,
        key_points: list[str],
        source_info: dict[str, str],
        conclusion: str | None = None,
        style: str = "blue",
    ) -> Path:
        """生成总结页.

        Args:
            key_points: 核心要点列表
            source_info: 来源信息
            conclusion: 总结感悟
            style: 配色方案

        Returns:
            生成的图片路径
        """
        colors = self.COLOR_SCHEMES.get(style, self.COLOR_SCHEMES["blue"])

        html_content = self._render_template(
            "summary.html",
            {
                "key_points": key_points,
                "source_info": source_info,
                "conclusion": conclusion or "",
                "colors": colors,
                "page_width": self.PAGE_WIDTH,
                "page_height": self.PAGE_HEIGHT,
            },
        )

        output_path = self.output_dir / "summary.png"
        await self._html_to_image(html_content, output_path)

        logger.info("总结页生成完成", path=str(output_path))
        return output_path

    async def generate_transcript_pages(
        self,
        structured_content: dict[str, Any],
        source_info: dict[str, str],
        style: str = "blue",
    ) -> list[Path]:
        """生成播客凝练版文字稿图片.

        使用 content_transcript.html 模板，按章节结构渲染。

        Args:
            structured_content: 结构化内容（含 sections）
            source_info: 来源信息
            style: 配色方案

        Returns:
            所有生成的图片路径列表
        """
        images: list[Path] = []
        sections = structured_content.get("sections", [])

        if not sections:
            # 回退到旧格式
            return await self.generate_note_images(structured_content, source_info, style)

        colors = self.COLOR_SCHEMES.get(style, self.COLOR_SCHEMES["blue"])
        total_pages = len(sections) + 1  # +1 总结页

        # 生成每页（每页一个章节）
        for i, section in enumerate(sections, 1):
            html_content = self._render_template(
                "content_transcript.html",
                {
                    "page_num": i,
                    "total_pages": total_pages,
                    "section_title": section.get("section_title", ""),
                    "chapter_title": section.get("section_title", ""),
                    "subsections": section.get("subsections", []),
                    "source_info": source_info,
                    "colors": colors,
                    "page_width": self.PAGE_WIDTH,
                    "page_height": self.PAGE_HEIGHT,
                },
            )

            output_path = self.output_dir / f"content_{i:02d}.png"
            await self._html_to_image(html_content, output_path)
            images.append(output_path)
            logger.info("文字稿页生成完成", page=i, path=str(output_path))

        return images

    async def generate_v9_note_images(
        self,
        structured_content: dict[str, Any],
        source_info: dict[str, str],
        style: str = "blue",
    ) -> list[Path]:
        """生成v9深度分析型笔记图片集.

        页面结构：封面 → 概要目录（含数据摘要）→ 详细内容（智能分页）→ 思考总结 → 出处标注
        
        智能分页规则：
        - 单页最多容纳 3 个子话题
        - 如果一个阶段有超过3个话题，自动拆分为多页
        - 每个拆分页保留相同的阶段标题和时间范围

        Args:
            structured_content: 结构化内容（含stages格式和key_data_summary）
            source_info: 来源信息
            style: 配色方案

        Returns:
            所有生成的图片路径列表
        """
        images: list[Path] = []
        colors = self.COLOR_SCHEMES.get(style, self.COLOR_SCHEMES["blue"])
        stages = structured_content.get("stages", [])
        reflections = structured_content.get("reflections", [])
        key_data_summary = structured_content.get("key_data_summary", [])

        MAX_TOPICS_PER_PAGE = 3  # 每页最多容纳的子话题数

        # 计算总内容页数（基于话题数量动态计算）
        content_page_count = 0
        for stage in stages:
            topics_count = len(stage.get("topics", []))
            pages_for_stage = (topics_count + MAX_TOPICS_PER_PAGE - 1) // MAX_TOPICS_PER_PAGE
            content_page_count += max(pages_for_stage, 1)

        total_pages = 1 + 1 + content_page_count + 1 + 1  # 封面+概要+内容+思考+出处

        # 1. 封面图
        cover = await self.generate_cover(
            title=structured_content.get("hook_title", "播客笔记"),
            podcast_name=source_info.get("podcast_name", ""),
            episode_title=source_info.get("episode_title", ""),
            guests=source_info.get("guests", ""),
            style=style,
        )
        images.append(cover)

        # 2. 概要目录页（含核心数据摘要）
        total_topics = sum(len(stage.get("topics", [])) for stage in stages)
        outline_html = self._render_template(
            "summary_outline.html",
            {
                "stages": stages,
                "total_topics": total_topics,
                "total_pages": total_pages,
                "key_data_summary": key_data_summary,
                "source_info": source_info,
                "colors": colors,
                "page_width": self.PAGE_WIDTH,
                "page_height": self.PAGE_HEIGHT,
            },
        )
        outline_path = self.output_dir / "content_01_outline.png"
        await self._html_to_image(outline_html, outline_path)
        images.append(outline_path)
        logger.info("概要目录页生成完成", path=str(outline_path))

        # 3. 详细内容页（智能动态分页）
        current_page_num = 3  # 封面(1) + 概要(2)，从第3页开始
        for i, stage in enumerate(stages, 1):
            topics = stage.get("topics", [])
            
            if len(topics) <= MAX_TOPICS_PER_PAGE:
                # 话题数不超过上限，单页渲染
                detail_html = self._render_template(
                    "content_detailed.html",
                    {
                        "page_num": current_page_num,
                        "total_pages": total_pages,
                        "stage_num": i,
                        "stage_title": stage.get("stage_title", ""),
                        "time_range": stage.get("time_range", ""),
                        "topics": topics,
                        "source_info": source_info,
                        "colors": colors,
                        "page_width": self.PAGE_WIDTH,
                        "page_height": self.PAGE_HEIGHT,
                    },
                )
                detail_path = self.output_dir / f"content_{current_page_num:02d}.png"
                await self._html_to_image(detail_html, detail_path)
                images.append(detail_path)
                logger.info("详细内容页生成完成", stage=i, page=current_page_num, topics=len(topics))
                current_page_num += 1
            else:
                # 话题数超过上限，按MAX_TOPICS_PER_PAGE拆分为多页
                for chunk_start in range(0, len(topics), MAX_TOPICS_PER_PAGE):
                    chunk_topics = topics[chunk_start : chunk_start + MAX_TOPICS_PER_PAGE]
                    
                    detail_html = self._render_template(
                        "content_detailed.html",
                        {
                            "page_num": current_page_num,
                            "total_pages": total_pages,
                            "stage_num": i,
                            "stage_title": stage.get("stage_title", ""),
                            "time_range": stage.get("time_range", ""),
                            "topics": chunk_topics,
                            "source_info": source_info,
                            "colors": colors,
                            "page_width": self.PAGE_WIDTH,
                            "page_height": self.PAGE_HEIGHT,
                        },
                    )
                    detail_path = self.output_dir / f"content_{current_page_num:02d}.png"
                    await self._html_to_image(detail_html, detail_path)
                    images.append(detail_path)
                    logger.info(
                        "详细内容页生成完成（拆分）",
                        stage=i,
                        page=current_page_num,
                        topics=len(chunk_topics),
                        chunk=(chunk_start // MAX_TOPICS_PER_PAGE) + 1,
                    )
                    current_page_num += 1

        # 4. 思考总结页
        thinking_page_num = total_pages - 1
        thinking_html = self._render_template(
            "thinking.html",
            {
                "page_num": thinking_page_num,
                "total_pages": total_pages,
                "reflections": reflections,
                "source_info": source_info,
                "colors": colors,
                "page_width": self.PAGE_WIDTH,
                "page_height": self.PAGE_HEIGHT,
            },
        )
        thinking_path = self.output_dir / f"content_{thinking_page_num:02d}_thinking.png"
        await self._html_to_image(thinking_html, thinking_path)
        images.append(thinking_path)
        logger.info("思考总结页生成完成", path=str(thinking_path))

        # 5. 出处标注页（使用summary模板）
        all_points = []
        for stage in stages:
            for topic in stage.get("topics", []):
                for point in topic.get("points", []):
                    all_points.append(point.get("text", "")[:30])

        summary = await self.generate_summary_page(
            key_points=all_points[:8],
            source_info=source_info,
            conclusion=structured_content.get("thinking", ""),
            style=style,
        )
        images.append(summary)

        logger.info("v9完整笔记图片生成完成", total=len(images), stages=len(stages), content_pages=content_page_count)
        return images

    async def generate_note_images(
        self,
        structured_content: dict[str, Any],
        source_info: dict[str, str],
        style: str = "blue",
    ) -> list[Path]:
        """生成完整的笔记图片集.

        自动检测内容格式，使用合适的模板。

        Args:
            structured_content: 结构化内容
            source_info: 来源信息
            style: 配色方案

        Returns:
            所有生成的图片路径列表
        """
        images: list[Path] = []

        # 1. 封面图
        cover = await self.generate_cover(
            title=structured_content.get("hook_title", "播客笔记"),
            podcast_name=source_info.get("podcast_name", ""),
            episode_title=source_info.get("episode_title", ""),
            guests=source_info.get("guests", ""),
            style=style,
        )
        images.append(cover)

        # 2. 检测内容格式
        if "stages" in structured_content:
            # v9格式：深度分析型
            return await self.generate_v9_note_images(
                structured_content=structured_content,
                source_info=source_info,
                style=style,
            )
        elif "sections" in structured_content:
            # v8格式：播客凝练版文字稿
            transcript_pages = await self.generate_transcript_pages(
                structured_content=structured_content,
                source_info=source_info,
                style=style,
            )
            images.extend(transcript_pages)
        else:
            # 旧格式：要点卡片
            key_points = structured_content.get("key_points", [])
            quotes = structured_content.get("quotes", [])

            page_size = 2  # 每页2个要点
            for i in range(0, len(key_points), page_size):
                page_points = key_points[i : i + page_size]
                page_quotes = quotes[i : i + page_size] if quotes else []

                page = await self.generate_content_page(
                    page_num=len(images),
                    section_title="核心观点",
                    key_points=page_points,
                    quotes=page_quotes,
                    source_info=source_info,
                    style=style,
                )
                images.append(page)

        # 3. 总结页
        if "sections" in structured_content:
            # v8格式：从 sections 提取要点
            all_points = []
            for section in structured_content.get("sections", []):
                for sub in section.get("subsections", []):
                    for point in sub.get("points", []):
                        all_points.append(point.get("text", "")[:30])
            key_points_for_summary = all_points[:6]
        else:
            key_points_for_summary = [p.get("title", "") for p in structured_content.get("key_points", [])]

        summary = await self.generate_summary_page(
            key_points=key_points_for_summary,
            source_info=source_info,
            conclusion=structured_content.get("conclusion", ""),
            style=style,
        )
        images.append(summary)

        logger.info("完整笔记图片生成完成", total=len(images))
        return images

    def _render_template(self, template_name: str, variables: dict[str, Any]) -> str:
        """渲染 HTML 模板.

        Args:
            template_name: 模板文件名
            variables: 模板变量

        Returns:
            渲染后的 HTML 字符串
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**variables)

    async def _html_to_image(self, html_content: str, output_path: Path) -> None:
        """将 HTML 渲染为图片.

        Args:
            html_content: HTML 内容
            output_path: 输出图片路径
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={
                    "width": self.PAGE_WIDTH,
                    "height": self.PAGE_HEIGHT,
                },
                device_scale_factor=self.DEVICE_SCALE,
            )

            await page.set_content(html_content)
            # 等待字体加载完成
            await page.wait_for_timeout(500)

            await page.screenshot(
                path=str(output_path),
                full_page=False,
                type="png",
            )

            await browser.close()

    def _safe_filename(self, text: str) -> str:
        """生成安全的文件名.

        Args:
            text: 原始文本

        Returns:
            安全的文件名
        """
        safe = "".join(c for c in text if c.isalnum() or c in (" ", "-", "_")).strip()
        return safe[:30] if safe else "untitled"
