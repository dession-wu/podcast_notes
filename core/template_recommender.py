"""模板推荐引擎 — 基于内容特征智能推荐笔记模板.

提供内容特征分析和模板推荐决策能力。
"""

from __future__ import annotations

import re
from typing import Any

from models.template import ContentFeatures, TemplateMetadata, TemplateRecommendation


# 模板注册表：所有可用模板的元数据
TEMPLATE_REGISTRY: list[TemplateMetadata] = [
    TemplateMetadata(
        alias="v9",
        name="深度分析型",
        description="时间线+阶段划分+标签化，信息密度最高",
        category="图文笔记",
        tags=["商业", "历史", "投资", "深度访谈"],
        output_format="stages_json",
        is_visual=True,
    ),
    TemplateMetadata(
        alias="v8",
        name="凝练文稿型",
        description="忠于播客原结构，删减口语化内容",
        category="图文笔记",
        tags=["对话", "访谈", "纪实"],
        output_format="sections_json",
        is_visual=True,
    ),
    TemplateMetadata(
        alias="v7",
        name="知识翻译官",
        description="用生活类比解释专业概念",
        category="图文笔记",
        tags=["科普", "方法论", "概念解读"],
        output_format="key_points_json",
        is_visual=True,
    ),
    TemplateMetadata(
        alias="v7d",
        name="图文高密度型",
        description="信息密度更高的图文排版",
        category="图文笔记",
        tags=["内容量大", "信息密集"],
        output_format="key_points_json",
        is_visual=True,
    ),
    TemplateMetadata(
        alias="v6",
        name="故事共鸣型",
        description="叙事驱动，强调情感共鸣",
        category="文字笔记",
        tags=["个人成长", "情感", "故事"],
        output_format="text",
        is_visual=False,
    ),
    TemplateMetadata(
        alias="v5",
        name="干货清单型",
        description="条目化呈现，actionable",
        category="文字笔记",
        tags=["技巧", "工具", "清单"],
        output_format="text",
        is_visual=False,
    ),
    TemplateMetadata(
        alias="v4",
        name="真人笔记型",
        description="降低 AI 感，像真人手写",
        category="文字笔记",
        tags=["追求真实感", "去 AI 化"],
        output_format="text",
        is_visual=False,
    ),
    TemplateMetadata(
        alias="v3",
        name="故事共鸣型（经典）",
        description="情感驱动、引发共鸣",
        category="文字笔记",
        tags=["生活", "情感类"],
        output_format="text",
        is_visual=False,
    ),
    TemplateMetadata(
        alias="v2",
        name="深度干货型（经典）",
        description="知识密集、逻辑严密",
        category="文字笔记",
        tags=["商业", "科技", "理财"],
        output_format="text",
        is_visual=False,
    ),
    TemplateMetadata(
        alias="v1",
        name="标准型（经典）",
        description="平衡信息量与可读性",
        category="文字笔记",
        tags=["通用场景"],
        output_format="text",
        is_visual=False,
    ),
]

# 别名到元数据的快速查找
_TEMPLATE_MAP: dict[str, TemplateMetadata] = {
    t.alias: t for t in TEMPLATE_REGISTRY
}


class ContentAnalyzer:
    """内容特征分析器.

    从转录文本中提取多维特征向量。
    """

    # 概念关键词库
    CONCEPT_KEYWORDS = [
        "理论", "模型", "框架", "原则", "方法论",
        "效应", "定律", "法则", "范式", "机制",
        "算法", "策略", "体系", "结构", "逻辑",
    ]

    # 叙事关键词库
    NARRATIVE_KEYWORDS = [
        "说", "认为", "提到", "分享", "讲述",
        "故事", "经历", "回忆", "记得", "当时",
        "后来", "然后", "接着", "最后",
    ]

    # 情感关键词库
    EMOTIONAL_KEYWORDS = [
        "感动", "震撼", "惊讶", "兴奋", "开心",
        "难过", "失望", "愤怒", "焦虑", "期待",
        "喜欢", "讨厌", "爱", "恨", "怕",
        "！", "!!", "？", "??",
    ]

    def analyze(self, text: str) -> ContentFeatures:
        """分析文本内容特征.

        Args:
            text: 转录文本

        Returns:
            内容特征向量
        """
        if not text or len(text.strip()) < 10:
            return ContentFeatures(confidence=0.0)

        # 预处理
        clean_text = text.strip()
        sentences = re.split(r'[。！？\n]+', clean_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = max(len(sentences), 1)

        # 1. 时间线密度
        year_patterns = [
            r'\d{4}年',
            r'(20\d{2}|19\d{2})',
            r'\d{4}-\d{2}',
            r'\d{4}/\d{2}',
        ]
        year_matches = sum(
            len(re.findall(p, clean_text))
            for p in year_patterns
        )
        time_line_density = min(year_matches / sentence_count, 1.0)

        # 2. 数据密度
        data_patterns = [
            r'\d+%',
            r'\d+万',
            r'\d+亿',
            r'\d+\.\d+',
            r'\d+个',
            r'第\d+',
        ]
        data_matches = sum(
            len(re.findall(p, clean_text))
            for p in data_patterns
        )
        data_density = min(data_matches / sentence_count, 1.0)

        # 3. 概念密度
        concept_matches = sum(
            1 for kw in self.CONCEPT_KEYWORDS
            if kw in clean_text
        )
        concept_density = min(concept_matches / sentence_count, 1.0)

        # 4. 叙事密度
        narrative_matches = sum(
            1 for kw in self.NARRATIVE_KEYWORDS
            if kw in clean_text
        )
        narrative_density = min(narrative_matches / sentence_count, 1.0)

        # 5. 情感密度
        emotional_matches = sum(
            1 for kw in self.EMOTIONAL_KEYWORDS
            if kw in clean_text
        )
        emotional_density = min(emotional_matches / sentence_count, 1.0)

        # 6. 置信度（基于文本长度）
        text_length = len(clean_text)
        if text_length > 2000:
            confidence = 0.95
        elif text_length > 1000:
            confidence = 0.85
        elif text_length > 500:
            confidence = 0.70
        elif text_length > 200:
            confidence = 0.50
        else:
            confidence = 0.30

        return ContentFeatures(
            time_line_density=round(time_line_density, 2),
            data_density=round(data_density, 2),
            concept_density=round(concept_density, 2),
            narrative_density=round(narrative_density, 2),
            emotional_density=round(emotional_density, 2),
            text_length=text_length,
            confidence=round(confidence, 2),
        )


class RecommendationEngine:
    """模板推荐决策器.

    基于内容特征，通过决策规则推荐最合适的模板。
    """

    def __init__(self) -> None:
        """初始化推荐引擎."""
        self.analyzer = ContentAnalyzer()

    def recommend(self, text: str) -> TemplateRecommendation:
        """为文本推荐最合适的模板.

        Args:
            text: 转录文本

        Returns:
            模板推荐结果
        """
        features = self.analyzer.analyze(text)

        # 如果文本过短，返回默认推荐
        if features.confidence < 0.3:
            return self._default_recommendation(features)

        # 决策规则（按优先级排序）
        # Rule 1: 时间线 + 数据密集 → 深度分析型
        if features.time_line_density > 0.6 and features.data_density > 0.5:
            return self._build_recommendation(
                template_alias="v9",
                reason="检测到丰富的时间线和数据，适合阶段化分析",
                features=features,
            )

        # Rule 2: 对话感强 + 时间线弱 → 凝练文稿型
        if features.narrative_density > 0.7 and features.time_line_density < 0.3:
            return self._build_recommendation(
                template_alias="v8",
                reason="对话感强，适合保留原播客结构",
                features=features,
            )

        # Rule 3: 概念密集 → 知识翻译官
        if features.concept_density > 0.6:
            return self._build_recommendation(
                template_alias="v7",
                reason="专业概念密集，适合通俗化解读",
                features=features,
            )

        # Rule 4: 叙事密集 → 故事共鸣型
        if features.narrative_density > 0.6:
            return self._build_recommendation(
                template_alias="v6",
                reason="故事性强，适合叙事化呈现",
                features=features,
            )

        # Rule 5: 数据密集 + 概念稀疏 → 干货清单型
        if features.data_density > 0.4 and features.concept_density < 0.3:
            return self._build_recommendation(
                template_alias="v5",
                reason="信息密度高，适合条目化呈现",
                features=features,
            )

        # Rule 6: 情感密集 → 故事共鸣型
        if features.emotional_density > 0.5:
            return self._build_recommendation(
                template_alias="v6",
                reason="情感表达丰富，适合共鸣型呈现",
                features=features,
            )

        # 默认：深度分析型
        return self._build_recommendation(
            template_alias="v9",
            reason="通用场景，结构化分析",
            features=features,
        )

    def _build_recommendation(
        self,
        template_alias: str,
        reason: str,
        features: ContentFeatures,
    ) -> TemplateRecommendation:
        """构建推荐结果.

        Args:
            template_alias: 推荐模板别名
            reason: 推荐原因
            features: 内容特征

        Returns:
            完整的推荐结果
        """
        template = _TEMPLATE_MAP.get(template_alias)
        if not template:
            template = _TEMPLATE_MAP["v9"]
            template_alias = "v9"

        # 计算推荐置信度
        confidence = self._calculate_confidence(features, template_alias)

        # 生成备选列表（排除已推荐的，按相关性排序）
        alternatives = self._get_alternatives(template_alias, features)

        return TemplateRecommendation(
            recommended_template=template_alias,
            recommended_name=template.name,
            confidence=round(confidence, 2),
            reason=reason,
            features=features,
            alternatives=alternatives,
        )

    def _default_recommendation(
        self,
        features: ContentFeatures,
    ) -> TemplateRecommendation:
        """返回默认推荐（文本过短时）.

        Args:
            features: 内容特征

        Returns:
            默认推荐结果
        """
        return TemplateRecommendation(
            recommended_template="v9",
            recommended_name="深度分析型",
            confidence=0.5,
            reason="文本较短，使用默认模板",
            features=features,
            alternatives=["v8", "v7"],
        )

    def _calculate_confidence(
        self,
        features: ContentFeatures,
        template_alias: str,
    ) -> float:
        """计算推荐置信度.

        基于特征区分度和模板匹配度计算。

        Args:
            features: 内容特征
            template_alias: 推荐模板

        Returns:
            置信度分数 (0-1)
        """
        base_confidence = features.confidence

        # 根据模板类型调整
        if template_alias == "v9":
            # 深度分析型依赖时间线和数据
            match_score = (
                features.time_line_density * 0.4 +
                features.data_density * 0.4 +
                features.concept_density * 0.2
            )
        elif template_alias == "v8":
            # 凝练文稿型依赖叙事
            match_score = (
                features.narrative_density * 0.6 +
                (1 - features.time_line_density) * 0.4
            )
        elif template_alias == "v7":
            # 知识翻译官依赖概念
            match_score = features.concept_density
        elif template_alias == "v6":
            # 故事共鸣型依赖叙事和情感
            match_score = (
                features.narrative_density * 0.5 +
                features.emotional_density * 0.5
            )
        elif template_alias == "v5":
            # 干货清单型依赖数据
            match_score = features.data_density
        else:
            match_score = 0.5

        # 综合置信度
        return base_confidence * 0.3 + match_score * 0.7

    def _get_alternatives(
        self,
        excluded_alias: str,
        features: ContentFeatures,
    ) -> list[str]:
        """获取备选模板列表.

        Args:
            excluded_alias: 已推荐的模板别名（需排除）
            features: 内容特征

        Returns:
            备选模板别名列表（按匹配度排序）
        """
        scores: dict[str, float] = {}

        for alias, template in _TEMPLATE_MAP.items():
            if alias == excluded_alias:
                continue

            # 计算每个模板的匹配分数
            if alias == "v9":
                score = (
                    features.time_line_density * 0.4 +
                    features.data_density * 0.4 +
                    features.concept_density * 0.2
                )
            elif alias == "v8":
                score = (
                    features.narrative_density * 0.6 +
                    (1 - features.time_line_density) * 0.4
                )
            elif alias == "v7":
                score = features.concept_density
            elif alias == "v6":
                score = (
                    features.narrative_density * 0.5 +
                    features.emotional_density * 0.5
                )
            elif alias == "v5":
                score = features.data_density
            else:
                score = 0.3

            scores[alias] = score

        # 按分数排序，取前 3 个
        sorted_aliases = sorted(
            scores.keys(),
            key=lambda a: scores[a],
            reverse=True,
        )
        return sorted_aliases[:3]


def get_template_by_alias(alias: str) -> TemplateMetadata | None:
    """通过别名获取模板元数据.

    Args:
        alias: 模板别名

    Returns:
        模板元数据，不存在则返回 None
    """
    return _TEMPLATE_MAP.get(alias)


def get_all_templates() -> list[TemplateMetadata]:
    """获取所有模板元数据.

    Returns:
        模板元数据列表
    """
    return TEMPLATE_REGISTRY.copy()


def get_visual_templates() -> list[TemplateMetadata]:
    """获取所有图文笔记模板.

    Returns:
        图文笔记模板列表
    """
    return [t for t in TEMPLATE_REGISTRY if t.is_visual]


def get_text_templates() -> list[TemplateMetadata]:
    """获取所有文字笔记模板.

    Returns:
        文字笔记模板列表
    """
    return [t for t in TEMPLATE_REGISTRY if not t.is_visual]
