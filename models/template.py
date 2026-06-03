"""模板推荐系统数据模型."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class ContentFeatures(BaseModel):
    """内容特征向量.

    从转录文本中提取的多维特征，用于模板推荐决策。
    """

    time_line_density: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="时间线密度：年份、时间段的提及频率",
    )
    data_density: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="数据密度：数字、百分比、金额的提及频率",
    )
    concept_density: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="概念密度：专业术语、方法论的提及频率",
    )
    narrative_density: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="叙事密度：故事、经历、对话的提及频率",
    )
    emotional_density: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="情感密度：情感词、感叹的提及频率",
    )
    text_length: int = Field(0, ge=0, description="文本长度（字符数）")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="特征提取置信度",
    )


class TemplateMetadata(BaseModel):
    """模板元数据.

    描述一个笔记模板的基本信息，用于前端展示和推荐说明。
    """

    alias: str = Field(..., description="模板别名（如 v9）")
    name: str = Field(..., description="人话名称（如 深度分析型）")
    description: str = Field(..., description="一句话描述模板特点")
    category: Literal["图文笔记", "文字笔记"] = Field(..., description="模板分类")
    tags: list[str] = Field(default_factory=list, description="适用场景标签")
    output_format: str = Field(..., description="输出格式（如 stages_json）")
    is_visual: bool = Field(False, description="是否生成图文")


class TemplateRecommendation(BaseModel):
    """模板推荐结果.

    包含系统推荐的模板及原因说明。
    """

    recommended_template: str = Field(..., description="推荐模板别名")
    recommended_name: str = Field(..., description="推荐模板人话名称")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="推荐置信度",
    )
    reason: str = Field(..., description="推荐原因（用户可见）")
    features: ContentFeatures = Field(..., description="分析的内容特征")
    alternatives: list[str] = Field(
        default_factory=list,
        description="备选模板别名（按匹配度排序）",
    )
