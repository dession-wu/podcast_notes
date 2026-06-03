"""内容处理模块 — 将转录文本提炼为小红书风格笔记.

处理流程：
1. 文本预处理（分段、去口头禅）
2. 内容理解（提取核心论点、金句）
3. 小红书风格化（套用模板生成文案）
4. 质量检查（字数、标签、合规性）
5. 图文生成（HTML渲染为图片）
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config import settings
from core.image_generator import ImageGenerator
from models.transcript import Transcript
from models.visual_note import VisualXiaohongshuNote
from models.xiaohongshu import XiaohongshuNote
from services.llm_service import LLMService, LLMServiceError
from utils import get_logger

logger = get_logger(__name__)


class ContentProcessorError(Exception):
    """内容处理相关错误."""

    pass


class ContentProcessor:
    """内容处理器.

    将播客转录文本转化为小红书风格的图文笔记。
    """

    # 常见口头禅和填充词（用于文本清洗）
    FILLER_WORDS = [
        r"嗯+[,.，。]?",
        r"啊+[,.，。]?",
        r"那个[,.，。]?",
        r"就是[,.，。]?",
        r"然后[,.，。]?",
        r"所以[,.，。]?",
        r"其实[,.，。]?",
        r"可能[,.，。]?",
        r"大概[,.，。]?",
        r"基本上[,.，。]?",
        r"怎么说呢[,.，。]?",
        r"你知道[吗吧]?[,.，。]?",
        r"我觉得[,.，。]?",
        r"我认为[,.，。]?",
    ]

    # 小红书文案约束
    NOTE_CONSTRAINTS = {
        "min_word_count": 100,
        "max_word_count": 800,
        "min_tags": 3,
        "max_tags": 5,
        "title_max_length": 20,
    }

    # 可用模板列表
    AVAILABLE_TEMPLATES = {
        "v1": "xiaohongshu_note_v1",               # 原版标准模板
        "v2": "xiaohongshu_note_v2",               # 深度干货型
        "v3": "xiaohongshu_note_v3",               # 故事共鸣型
        "v4": "xiaohongshu_note_v4_humanized",     # 真人笔记型（降低AI感）
        "v5": "xiaohongshu_note_v5_dry_goods",     # 知识翻译官型
        "v6": "xiaohongshu_note_v6_story",         # 故事型
        "v7": "xiaohongshu_note_v7_visual",        # 图文结构化型
        "v7d": "xiaohongshu_note_v7_visual_dense",  # 图文高密度型
        "v8": "xiaohongshu_note_v8_transcript",    # 播客凝练版文字稿
        "v9": "xiaohongshu_note_v9_analysis",      # 深度分析型（阶段+标签+因果链）
    }

    def __init__(self, llm_service: LLMService | None = None) -> None:
        """初始化内容处理器.

        Args:
            llm_service: LLM 服务实例，默认创建新实例
        """
        self.llm = llm_service or LLMService()
        self.output_dir = settings.output_dir

        logger.info("内容处理器初始化完成")

    def process(
        self,
        transcript: Transcript,
        template_name: str = "xiaohongshu_note_v1",
        **kwargs: Any,
    ) -> XiaohongshuNote | VisualXiaohongshuNote:
        """处理转录文本生成小红书笔记.

        Args:
            transcript: 转录文本对象
            template_name: 使用的 Prompt 模板名称
            **kwargs: 额外参数（如自定义标题、标签等）

        Returns:
            小红书笔记对象（纯文字或图文）

        Raises:
            ContentProcessorError: 处理失败
        """
        logger.info(
            "开始内容处理",
            episode=transcript.episode_title,
            word_count=transcript.word_count,
            template=template_name,
        )

        # 步骤 1: 文本预处理
        cleaned_text = self._preprocess_text(transcript.text)

        # 步骤 2: 内容理解（提取关键信息）
        key_info = self._extract_key_info(cleaned_text)

        # 步骤 3: 小红书风格化
        note = self._generate_note(
            transcript=transcript,
            cleaned_text=cleaned_text,
            key_info=key_info,
            template_name=template_name,
            **kwargs,
        )

        # 步骤 4: 质量检查
        note = self._quality_check(note)

        # 如果是图文模板，生成图片
        if template_name in ("v7", "xiaohongshu_note_v7_visual"):
            return self._generate_visual_note(
                transcript=transcript,
                text_note=note,
                cleaned_text=cleaned_text,
                key_info=key_info,
                **kwargs,
            )

        # 保存笔记
        self._save_note(note)

        logger.info(
            "内容处理完成",
            episode=transcript.episode_title,
            note_title=note.title,
            note_word_count=note.word_count,
        )

        return note

    def _preprocess_text(self, text: str) -> str:
        """预处理转录文本.

        - 去除多余空白
        - 去除口头禅
        - 合并短句

        Args:
            text: 原始转录文本

        Returns:
            清洗后的文本
        """
        # 去除多余空白
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)

        # 去除口头禅（不区分大小写）
        for pattern in self.FILLER_WORDS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # 合并连续标点
        text = re.sub(r"[,.，。]{2,}", "，", text)

        # 去除空行
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # 统计清洗效果
        original_length = len(text)
        cleaned_length = len(text)
        logger.debug(
            "文本预处理完成",
            original_chars=original_length,
            cleaned_chars=cleaned_length,
        )

        return text

    def _extract_key_info(self, text: str) -> dict[str, Any]:
        """提取转录文本中的关键信息.

        使用 LLM 按内容逻辑进行章节划分、内容扩展和标签提取。
        优化后的提取策略：保留更多原文细节，增加内容密度。

        Args:
            text: 清洗后的文本

        Returns:
            关键信息字典，包含 chapters、theme、key_points、quotes、tags
        """
        extraction_prompt = f"""请对以下播客转录文本进行深度结构化提取：

{text}

请提取以下内容（使用中文回答）：

1. 按照文稿的内容逻辑进行章节划分，同时拟定好标题、小标题等
2. 对文稿内容进行详细提炼和扩展，保留核心论述、关键数据、重要案例和逻辑链条
3. 撰写总结感悟，以资深投资前辈的视角分享深度见解
4. 适合的小红书话题标签（3-5 个）

请严格按以下格式输出：

主题：[一句话概括核心主题]

## 一、[章节标题]
### [小标题1]
详细提炼后的内容...【核心语句】...继续内容。要求保留原文的关键论述、数据支撑和案例细节，内容充实有信息量。
### [小标题2]
详细提炼后的内容...【核心语句】...继续内容。每个子话题下至少包含2-3个核心论述点。

## 二、[章节标题]
### [小标题1]
详细提炼后的内容...【核心语句】...继续内容。

总结感悟：
[以一位拥有15年以上投资经验、经历过完整牛熊周期的前辈视角，用平易近人的语气分享听后感悟。避免说教口吻，不堆砌术语，而是通过日常生活中的真实案例来阐述投资理念。字数要求150-250字，内容需包含：一个与主题相关的生活化类比或案例、对普通听众的具体行动建议、以及体现个人经验沉淀的深度思考。语气像一位有经验的朋友在聊天，而非老师在讲课。]

标签：
- [标签1]
- [标签2]
- [标签3]

要求：
- 章节划分应严格遵循文稿的内在逻辑和时间线，不要强行均分
- 每个章节至少包含2个小标题，每个小标题下内容充实
- 提炼后的内容必须保留：核心观点、关键数据、重要案例、论证逻辑、因果链条
- 用【】标注的核心语句应是最有价值的观点、结论或数据
- 内容量要求：每个子话题的提炼内容不少于80字，确保信息密度充足
- 禁止简单概括或一句话带过，必须展开论述
- 总结感悟必须体现：生活化案例 + 具体建议 + 深度思考，避免空泛的"受益匪浅"
- 标签应贴合内容领域，适合小红书传播
"""

        try:
            result = self.llm.generate(
                prompt=extraction_prompt,
                temperature=0.3,
                max_tokens=4000,
            )
            return self._parse_extraction_result(result)
        except LLMServiceError as e:
            logger.warning(f"关键信息提取失败，使用 fallback: {e}")
            return self._fallback_extraction(text)

    def _parse_extraction_result(self, result: str) -> dict[str, Any]:
        """解析 LLM 提取的结果.

        解析章节化格式，同时派生 key_points 和 quotes 以保持向后兼容。

        Args:
            result: LLM 返回的提取结果

        Returns:
            结构化的关键信息字典
        """
        info: dict[str, Any] = {
            "theme": "",
            "chapters": [],
            "key_points": [],
            "quotes": [],
            "tags": [],
            "conclusion": "",
        }

        theme_match = re.search(r"主题[：:]\s*(.+)", result)
        if theme_match:
            info["theme"] = theme_match.group(1).strip()

        conclusion_match = re.search(
            r"总结感悟[：:]\s*(.+?)(?=\n标签[：:]|$)",
            result,
            re.DOTALL,
        )
        if conclusion_match:
            info["conclusion"] = conclusion_match.group(1).strip()

        tags_section = re.search(
            r"标签[：:]\s*(.+?)$",
            result,
            re.DOTALL,
        )
        if tags_section:
            tags_text = tags_section.group(1)
            info["tags"] = [
                line.strip("- #").strip()
                for line in tags_text.split("\n")
                if line.strip().startswith("-")
            ]

        chapters = self._parse_chapters(result)
        info["chapters"] = chapters

        info["key_points"] = self._derive_key_points_from_chapters(chapters)
        info["quotes"] = self._derive_quotes_from_chapters(chapters)

        return info

    def _parse_chapters(self, text: str) -> list[dict[str, Any]]:
        """从 LLM 输出中解析章节结构.

        Args:
            text: LLM 输出的完整文本

        Returns:
            章节列表，每章包含 title 和 subsections
        """
        chapters: list[dict[str, Any]] = []

        chapter_splits = re.split(r"^##\s+", text, flags=re.MULTILINE)
        for chunk in chapter_splits[1:]:
            first_line = chunk.split("\n", 1)[0].strip()
            chapter_title = re.sub(r"^[一二三四五六七八九十]+[、.]\s*", "", first_line).strip()

            subsections: list[dict[str, Any]] = []

            sub_splits = re.split(r"^###\s+", chunk, flags=re.MULTILINE)
            for sub_chunk in sub_splits[1:]:
                sub_lines = sub_chunk.split("\n", 1)
                subtitle = sub_lines[0].strip()
                content = sub_lines[1].strip() if len(sub_lines) > 1 else ""

                highlights = re.findall(r"【(.+?)】", content)
                clean_content = re.sub(r"【(.+?)】", r"\1", content)

                subsections.append({
                    "subtitle": subtitle,
                    "content": clean_content,
                    "highlights": highlights,
                })

            if not subsections:
                body_match = re.search(r"\n(.+)", chunk, re.DOTALL)
                body = body_match.group(1).strip() if body_match else ""
                highlights = re.findall(r"【(.+?)】", body)
                clean_body = re.sub(r"【(.+?)】", r"\1", body)
                if clean_body:
                    subsections.append({
                        "subtitle": chapter_title,
                        "content": clean_body,
                        "highlights": highlights,
                    })

            if subsections:
                chapters.append({
                    "title": chapter_title,
                    "subsections": subsections,
                })

        return chapters

    @staticmethod
    def _derive_key_points_from_chapters(chapters: list[dict[str, Any]]) -> list[str]:
        """从章节结构中派生 key_points 以保持向后兼容.

        Args:
            chapters: 章节列表

        Returns:
            要点列表
        """
        points = []
        for chapter in chapters:
            for sub in chapter.get("subsections", []):
                if sub.get("highlights"):
                    points.extend(sub["highlights"][:2])
                elif sub.get("content"):
                    content = sub["content"]
                    points.append(content[:80] if len(content) > 80 else content)
        return points[:8]

    @staticmethod
    def _derive_quotes_from_chapters(chapters: list[dict[str, Any]]) -> list[str]:
        """从章节结构中派生 quotes 以保持向后兼容.

        Args:
            chapters: 章节列表

        Returns:
            金句列表
        """
        quotes = []
        for chapter in chapters:
            for sub in chapter.get("subsections", []):
                for h in sub.get("highlights", []):
                    quotes.append(h)
        return quotes[:5]

    def _fallback_extraction(self, text: str) -> dict[str, Any]:
        """当 LLM 提取失败时的备用方案.

        使用简单的启发式规则提取信息。

        Args:
            text: 清洗后的文本

        Returns:
            关键信息字典
        """
        theme = text[:100].strip()

        sentences = re.split(r"[。！？\n]", text)
        key_points = [
            s.strip() for s in sentences
            if len(s.strip()) > 20 and len(s.strip()) < 200
        ][:5]

        tags = ["播客推荐", "个人成长", "干货分享"]

        chapters = [{
            "title": "内容概要",
            "subsections": [{
                "subtitle": "核心要点",
                "content": " ".join(key_points[:3]),
                "highlights": key_points[:2],
            }],
        }]

        return {
            "theme": theme,
            "chapters": chapters,
            "key_points": key_points,
            "quotes": key_points[:2] if key_points else [],
            "tags": tags,
        }

    def _generate_note(
        self,
        transcript: Transcript,
        cleaned_text: str,
        key_info: dict[str, Any],
        template_name: str,
        **kwargs: Any,
    ) -> XiaohongshuNote:
        """生成小红书笔记.

        Args:
            transcript: 原始转录对象
            cleaned_text: 清洗后的文本
            key_info: 提取的关键信息
            template_name: 模板名称
            **kwargs: 额外参数

        Returns:
            小红书笔记对象
        """
        template_vars = {
            "podcast_title": transcript.podcast_name or "未知播客",
            "episode_title": transcript.episode_title,
            "theme": key_info.get("theme", ""),
            "key_points": key_info.get("key_points", []),
            "quotes": key_info.get("quotes", []),
            "chapters": key_info.get("chapters", []),
            "tags": key_info.get("tags", []),
            "transcript_summary": cleaned_text,
            **kwargs,
        }

        # 解析模板名称（支持别名）
        actual_template = self.AVAILABLE_TEMPLATES.get(template_name, template_name)

        # 使用模板生成
        try:
            note_content = self.llm.generate_with_template(
                template_name=actual_template,
                variables=template_vars,
                temperature=0.7,
                max_tokens=2000,
            )
        except LLMServiceError as e:
            logger.error(f"笔记生成失败: {e}")
            raise ContentProcessorError(f"笔记生成失败: {e}") from e

        # 解析生成的内容
        return self._parse_note_content(
            content=note_content,
            podcast_name=transcript.podcast_name,
            episode_title=transcript.episode_title,
            tags=key_info.get("tags", []),
        )

    def _parse_note_content(
        self,
        content: str,
        podcast_name: str | None,
        episode_title: str,
        tags: list[str],
    ) -> XiaohongshuNote:
        """解析 LLM 生成的笔记内容.

        Args:
            content: LLM 生成的原始内容
            podcast_name: 播客名称
            episode_title: 单集标题
            tags: 话题标签

        Returns:
            小红书笔记对象
        """
        # 提取标题（第一行或 ## 标记）
        title = ""
        title_match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # 取第一行非空内容
            first_line = content.split("\n")[0].strip()
            title = first_line[:20] if first_line else "播客笔记"

        # 清理标题标记
        title = re.sub(r"^#+\s*", "", title).strip()

        # 截断标题（小红书标题限制20字）
        if len(title) > 20:
            title = title[:20]

        # 提取正文（去除标题行）
        body_lines = []
        skip_first = bool(title_match)
        for line in content.split("\n"):
            if skip_first:
                skip_first = False
                continue
            body_lines.append(line)
        body = "\n".join(body_lines).strip()

        # 如果正文为空，使用全部内容
        if not body:
            body = content

        # 计算字数
        chinese_chars = sum(1 for c in body if "\u4e00" <= c <= "\u9fff")
        english_words = len([w for w in body.split() if w.isascii()])
        word_count = chinese_chars + english_words

        return XiaohongshuNote(
            title=title,
            content=body,
            tags=tags,
            source_podcast=podcast_name,
            source_episode=episode_title,
            word_count=word_count,
        )

    def _quality_check(self, note: XiaohongshuNote) -> XiaohongshuNote:
        """质量检查与修正.

        包含基础质量检查和AI感检测。

        Args:
            note: 待检查的笔记

        Returns:
            修正后的笔记
        """
        issues: list[str] = []

        # 检查字数
        if note.word_count < self.NOTE_CONSTRAINTS["min_word_count"]:
            issues.append(
                f"字数不足 ({note.word_count} < {self.NOTE_CONSTRAINTS['min_word_count']})"
            )
        elif note.word_count > self.NOTE_CONSTRAINTS["max_word_count"]:
            issues.append(
                f"字数超出 ({note.word_count} > {self.NOTE_CONSTRAINTS['max_word_count']})"
            )

        # 检查标签数量
        if len(note.tags) < self.NOTE_CONSTRAINTS["min_tags"]:
            issues.append(f"标签不足 ({len(note.tags)} < {self.NOTE_CONSTRAINTS['min_tags']})")
        elif len(note.tags) > self.NOTE_CONSTRAINTS["max_tags"]:
            # 截断多余标签
            note.tags = note.tags[: self.NOTE_CONSTRAINTS["max_tags"]]
            issues.append("标签数量已截断")

        # 检查标题长度
        if len(note.title) > self.NOTE_CONSTRAINTS["title_max_length"]:
            note.title = note.title[: self.NOTE_CONSTRAINTS["title_max_length"]]
            issues.append("标题已截断")

        # 检查来源标注
        if "本文灵感/内容提炼自播客" not in note.content:
            logger.warning("笔记缺少来源标注，已自动添加")
            # 来源标注会在 model 的 validator 中自动添加

        # AI感检测
        ai_markers = self._detect_ai_markers(note.content)
        if ai_markers:
            issues.append(f"检测到AI感标记: {', '.join(ai_markers)}")

        if issues:
            logger.warning("笔记质量检查发现问题", issues=issues)
        else:
            logger.info("笔记质量检查通过")

        return note

    def _detect_ai_markers(self, content: str) -> list[str]:
        """检测内容中的AI感标记.

        Args:
            content: 笔记内容

        Returns:
            检测到的AI标记列表
        """
        markers = []

        # 机械连接词
        mechanical_words = ["首先", "其次", "最后", "综上所述", "值得注意的是", "总而言之"]
        for word in mechanical_words:
            if word in content:
                markers.append(word)

        # 绝对化表述
        absolute_words = ["无敌", "闭眼入", "必看", "绝对", "一定", "必然"]
        for word in absolute_words:
            if word in content:
                markers.append(word)

        # 排比句检测（简单启发式）
        lines = content.split("\n")
        for i in range(len(lines) - 2):
            # 检测连续三行以相同标点结尾
            if all("。" in line for line in lines[i:i+3]):
                # 检查是否有明显的排比结构
                prefixes = [line[:3] for line in lines[i:i+3]]
                if len(set(prefixes)) < 3:  # 前缀相似度高
                    markers.append("排比句")
                    break

        return markers

    def _generate_visual_note(
        self,
        transcript: Transcript,
        text_note: XiaohongshuNote,
        cleaned_text: str,
        key_info: dict[str, Any],
        style: str = "blue",
        **kwargs: Any,
    ) -> VisualXiaohongshuNote:
        """生成图文笔记.

        Args:
            transcript: 原始转录对象
            text_note: 已生成的文字笔记
            cleaned_text: 清洗后的文本
            key_info: 提取的关键信息
            style: 配色方案
            **kwargs: 额外参数

        Returns:
            图文笔记对象
        """
        logger.info("开始生成图文笔记", episode=transcript.episode_title)

        # 确定使用的结构化提取模板
        template_alias = kwargs.get("template_alias", "v7")
        if template_alias == "v9":
            structured_template = "xiaohongshu_note_v9_analysis"
        elif template_alias == "v8":
            structured_template = "xiaohongshu_note_v8_transcript"
        else:
            structured_template = kwargs.get("structured_template", "xiaohongshu_note_v7_visual")

        # 1. 提取结构化内容
        structured_content = self._extract_structured_content(
            transcript=transcript,
            cleaned_text=cleaned_text,
            key_info=key_info,
            template_name=structured_template,
        )

        # 2. 准备来源信息
        source_info = {
            "podcast_name": transcript.podcast_name or "未知播客",
            "episode_title": transcript.episode_title,
            "guests": kwargs.get("guests", ""),
        }

        # 3. 生成图片
        image_gen = ImageGenerator(output_dir=self.output_dir / "images")
        try:
            import asyncio
            # v9使用stages格式，需要特殊处理
            if template_alias == "v9" or "stages" in structured_content:
                images = asyncio.run(
                    image_gen.generate_v9_note_images(
                        structured_content=structured_content,
                        source_info=source_info,
                        style=style,
                    )
                )
            else:
                images = asyncio.run(
                    image_gen.generate_note_images(
                        structured_content=structured_content,
                        source_info=source_info,
                        style=style,
                    )
                )
        except Exception as e:
            logger.error(f"图片生成失败: {e}")
            images = []

        # 4. 组装图文笔记
        visual_note = VisualXiaohongshuNote(
            text_note=text_note,
            image_paths=images,
            structured_content=structured_content,
            source_info=source_info,
            style=style,
        )

        # 5. 保存完整笔记
        visual_note.save_complete_note(self.output_dir)

        logger.info(
            "图文笔记生成完成",
            episode=transcript.episode_title,
            images=len(images),
        )

        return visual_note

    def _extract_structured_content(
        self,
        transcript: Transcript,
        cleaned_text: str,
        key_info: dict[str, Any],
        template_name: str = "xiaohongshu_note_v7_visual",
    ) -> dict[str, Any]:
        """提取结构化内容用于图片生成.

        使用 LLM 将内容转化为结构化 JSON。

        Args:
            transcript: 原始转录对象
            cleaned_text: 清洗后的文本
            key_info: 已提取的关键信息
            template_name: 使用的结构化提取模板

        Returns:
            结构化内容字典
        """
        template_vars = {
            "podcast_title": transcript.podcast_name or "未知播客",
            "episode_title": transcript.episode_title,
            "theme": key_info.get("theme", ""),
            "key_points": key_info.get("key_points", []),
            "quotes": key_info.get("quotes", []),
            "chapters": key_info.get("chapters", []),
            "transcript_summary": cleaned_text,
        }

        try:
            result = self.llm.generate_with_template(
                template_name=template_name,
                variables=template_vars,
                temperature=0.7,
                max_tokens=3000,
            )

            # 解析 JSON
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if json_match:
                structured = json.loads(json_match.group())
                return structured
            else:
                logger.warning("无法从 LLM 输出中解析 JSON，使用 fallback")
                return self._fallback_structured_content(key_info)

        except (LLMServiceError, json.JSONDecodeError) as e:
            logger.warning(f"结构化内容提取失败: {e}，使用 fallback")
            return self._fallback_structured_content(key_info)

    def _fallback_structured_content(
        self, key_info: dict[str, Any]
    ) -> dict[str, Any]:
        """结构化内容提取失败时的备用方案.

        Args:
            key_info: 已提取的关键信息

        Returns:
            基础结构化内容
        """
        key_points = key_info.get("key_points", [])
        quotes = key_info.get("quotes", [])

        return {
            "hook_title": key_info.get("theme", "播客笔记")[:20],
            "theme": key_info.get("theme", ""),
            "introduction": "听完这期播客，收获很大，整理了一些核心观点分享给大家。",
            "key_points": [
                {
                    "title": point[:15] if len(point) > 15 else point,
                    "content": point,
                    "highlight": "",
                    "analogy": "",
                }
                for point in key_points[:5]
            ],
            "quotes": [
                {"text": quote[:30], "speaker": "嘉宾"}
                for quote in quotes[:2]
            ],
            "timeline": [],
            "conclusion": "这期内容值得反复听，推荐给大家。",
            "tags": key_info.get("tags", ["播客笔记", "干货分享"]),
        }

    def _save_note(self, note: XiaohongshuNote) -> None:
        """保存笔记到文件.

        Args:
            note: 小红书笔记对象
        """
        safe_title = "".join(
            c for c in note.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()[:30]

        output_path = self.output_dir / f"{safe_title}_xiaohongshu.md"
        note.save_to_file(output_path)

        logger.info("小红书笔记已保存", path=str(output_path))

    def batch_process(
        self,
        transcripts: list[Transcript],
        template_name: str = "xiaohongshu_note_v1",
    ) -> list[XiaohongshuNote]:
        """批量处理转录文本.

        Args:
            transcripts: 转录文本对象列表
            template_name: 使用的模板名称

        Returns:
            小红书笔记对象列表
        """
        notes: list[XiaohongshuNote] = []

        for idx, transcript in enumerate(transcripts, 1):
            logger.info(
                "批量处理进度",
                current=idx,
                total=len(transcripts),
                episode=transcript.episode_title,
            )

            try:
                note = self.process(transcript, template_name)
                notes.append(note)
            except ContentProcessorError as e:
                logger.error(
                    "单集处理失败，跳过",
                    episode=transcript.episode_title,
                    error=str(e),
                )

        logger.info(
            "批量处理完成",
            total=len(transcripts),
            success=len(notes),
            failed=len(transcripts) - len(notes),
        )

        return notes
