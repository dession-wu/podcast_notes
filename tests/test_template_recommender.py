"""模板推荐引擎单元测试."""

from __future__ import annotations

import pytest

from core.template_recommender import (
    ContentAnalyzer,
    RecommendationEngine,
    TEMPLATE_REGISTRY,
    get_all_templates,
    get_template_by_alias,
    get_visual_templates,
    get_text_templates,
)
from models.template import ContentFeatures, TemplateMetadata


class TestContentAnalyzer:
    """内容特征分析器测试."""

    @pytest.fixture
    def analyzer(self) -> ContentAnalyzer:
        """创建分析器实例."""
        return ContentAnalyzer()

    def test_analyze_empty_text(self, analyzer: ContentAnalyzer) -> None:
        """测试空文本分析."""
        result = analyzer.analyze("")
        assert result.confidence == 0.0
        assert result.text_length == 0

    def test_analyze_short_text(self, analyzer: ContentAnalyzer) -> None:
        """测试短文本分析."""
        result = analyzer.analyze("这是一个短文本。")
        assert result.confidence < 0.5
        assert result.text_length < 200

    def test_analyze_timeline_dense_text(self, analyzer: ContentAnalyzer) -> None:
        """测试时间线密集文本."""
        text = """
        2008年金融危机爆发，全球经济受到重创，GDP下降5%。
        2010年中国经济开始复苏，GDP增长10%，出口增加20%。
        2012年欧债危机蔓延，影响全球金融市场，股市下跌30%。
        2015年A股市场大幅波动，投资者损失惨重，市值蒸发40%。
        2018年贸易战爆发，中美关系紧张，关税增加25%。
        2020年新冠疫情席卷全球，经济再次受挫，失业率上升15%。
        2022年全球经济逐步恢复，通胀压力上升，CPI增长8%。
        2024年人工智能爆发，科技行业迎来新机遇，投资增长50%。
        """
        result = analyzer.analyze(text)
        assert result.time_line_density > 0.5
        assert result.data_density > 0
        assert result.confidence >= 0.5

    def test_analyze_data_dense_text(self, analyzer: ContentAnalyzer) -> None:
        """测试数据密集文本."""
        text = """
        这家公司营收增长了35%，净利润率达到15%。
        市场份额从20%提升到28%，用户数量突破5000万。
        投资额高达2.5亿元，回报率超过120%。
        成本降低了18%，效率提升了40%。
        营收增长35%，利润提升20%。
        用户数量突破1000万，日活达到500万。
        市场份额从15%提升到25%。
        成本降低18%，效率提升40%。
        投资额2.5亿元，回报率120%。
        """
        result = analyzer.analyze(text)
        assert result.data_density > 0.3
        assert result.confidence > 0.3

    def test_analyze_concept_dense_text(self, analyzer: ContentAnalyzer) -> None:
        """测试概念密集文本."""
        text = """
        这个理论框架基于系统思维方法论。
        我们需要建立新的模型来理解这个效应。
        根据这个定律，可以推导出相应的法则。
        这个范式转变需要全新的策略和机制。
        """
        result = analyzer.analyze(text)
        assert result.concept_density > 0.3

    def test_analyze_narrative_text(self, analyzer: ContentAnalyzer) -> None:
        """测试叙事型文本."""
        text = """
        他回忆说，当时的情况非常艰难。
        然后，他分享了自己的经历。
        他认为，这个故事值得讲述。
        接着，他提到了那段回忆。
        最后，他说记得当时的情景。
        """
        result = analyzer.analyze(text)
        assert result.narrative_density > 0.3

    def test_analyze_emotional_text(self, analyzer: ContentAnalyzer) -> None:
        """测试情感型文本."""
        text = """
        这真的太令人感动了！
        我感到非常兴奋和开心！
        这个结果让人惊讶！
        我期待已久的时刻终于来了！
        """
        result = analyzer.analyze(text)
        assert result.emotional_density > 0.2


class TestRecommendationEngine:
    """推荐决策器测试."""

    @pytest.fixture
    def engine(self) -> RecommendationEngine:
        """创建推荐引擎实例."""
        return RecommendationEngine()

    def test_recommend_empty_text(self, engine: RecommendationEngine) -> None:
        """测试空文本推荐."""
        result = engine.recommend("")
        assert result.recommended_template == "v9"
        assert result.confidence < 0.6

    def test_recommend_short_text(self, engine: RecommendationEngine) -> None:
        """测试短文本推荐."""
        result = engine.recommend("这是一个短文本。")
        assert result.recommended_template == "v9"
        assert "文本较短" in result.reason

    def test_recommend_timeline_dense(self, engine: RecommendationEngine) -> None:
        """测试时间线密集文本推荐."""
        text = """
        2008年金融危机爆发，全球经济受到重创，GDP下降5%。
        2010年中国经济开始复苏，GDP增长10%，出口增加20%。
        2012年欧债危机蔓延，影响全球金融市场，股市下跌30%。
        2015年A股市场大幅波动，投资者损失惨重，市值蒸发40%。
        2018年贸易战爆发，中美关系紧张，关税增加25%。
        2020年新冠疫情席卷全球，经济再次受挫，失业率上升15%。
        2022年全球经济逐步恢复，通胀压力上升，CPI增长8%。
        2024年人工智能爆发，科技行业迎来新机遇，投资增长50%。
        """
        result = engine.recommend(text)
        assert result.recommended_template == "v9"
        assert "时间线" in result.reason
        assert result.confidence > 0.5

    def test_recommend_conversation_text(self, engine: RecommendationEngine) -> None:
        """测试对话型文本推荐."""
        text = """
        他说，我认为这个观点很有意思。
        然后她提到，我也这么觉得。
        接着他分享了自己的看法。
        她说，这个故事让我想起了自己的经历。
        他认为，我们应该多听听不同的声音。
        她回忆说，那时候真的很不容易。
        """
        result = engine.recommend(text)
        assert result.recommended_template == "v8"
        assert "对话" in result.reason or "结构" in result.reason

    def test_recommend_concept_text(self, engine: RecommendationEngine) -> None:
        """测试概念型文本推荐."""
        text = """
        这个理论框架基于系统思维方法论。
        我们需要建立新的模型来理解这个效应。
        根据这个定律，可以推导出相应的法则。
        这个范式转变需要全新的策略和机制。
        这个算法可以优化整个体系的结构。
        这个原则指导着我们的决策逻辑。
        """
        result = engine.recommend(text)
        assert result.recommended_template == "v7"
        assert "概念" in result.reason or "通俗化" in result.reason

    def test_recommend_story_text(self, engine: RecommendationEngine) -> None:
        """测试故事型文本推荐."""
        text = """
        这是一个关于成长的故事。
        他回忆起自己的经历，讲述了那段往事。
        然后，他分享了一个感人的故事。
        这个故事让人深受触动。
        他说，每个人的经历都值得被倾听。
        最后，他提到了那个改变一生的时刻。
        她回忆说，那时候真的很不容易。
        他认为，我们应该珍惜每一段经历。
        她提到，那个故事改变了她的人生。
        """
        result = engine.recommend(text)
        # Story-heavy text may trigger v6 (story) or v8 (transcript) depending on density
        assert result.recommended_template in ["v6", "v8"]
        assert "故事" in result.reason or "对话" in result.reason or "叙事" in result.reason

    def test_recommend_data_rich_text(self, engine: RecommendationEngine) -> None:
        """测试数据丰富文本推荐."""
        text = """
        营收增长35%，利润提升20%。
        用户数量突破1000万，日活达到500万。
        市场份额从15%提升到25%。
        成本降低18%，效率提升40%。
        投资额2.5亿元，回报率120%。
        """
        result = engine.recommend(text)
        # Should recommend v5 (干货清单型) or v9 (深度分析型)
        assert result.recommended_template in ["v5", "v9"]
        assert len(result.alternatives) > 0

    def test_recommendation_has_alternatives(
        self, engine: RecommendationEngine
    ) -> None:
        """测试推荐结果包含备选."""
        text = "这是一个关于商业投资的深度分析，涉及2008年金融危机和2015年股市波动。"
        result = engine.recommend(text)
        assert len(result.alternatives) > 0
        assert len(result.alternatives) <= 3

    def test_recommendation_features_included(
        self, engine: RecommendationEngine
    ) -> None:
        """测试推荐结果包含特征数据."""
        text = "这是一个测试文本，包含一些数据和概念。"
        result = engine.recommend(text)
        assert result.features is not None
        assert result.features.text_length > 0


class TestTemplateRegistry:
    """模板注册表测试."""

    def test_all_templates_have_required_fields(self) -> None:
        """测试所有模板都有必需字段."""
        for template in TEMPLATE_REGISTRY:
            assert template.alias
            assert template.name
            assert template.description
            assert template.category in ["图文笔记", "文字笔记"]
            assert template.output_format

    def test_template_aliases_are_unique(self) -> None:
        """测试模板别名唯一."""
        aliases = [t.alias for t in TEMPLATE_REGISTRY]
        assert len(aliases) == len(set(aliases))

    def test_get_template_by_alias(self) -> None:
        """测试通过别名获取模板."""
        template = get_template_by_alias("v9")
        assert template is not None
        assert template.alias == "v9"
        assert template.name == "深度分析型"

    def test_get_template_by_alias_not_found(self) -> None:
        """测试获取不存在的模板."""
        template = get_template_by_alias("nonexistent")
        assert template is None

    def test_get_all_templates(self) -> None:
        """测试获取所有模板."""
        templates = get_all_templates()
        assert len(templates) == len(TEMPLATE_REGISTRY)
        # Ensure it's a copy
        templates.pop()
        assert len(TEMPLATE_REGISTRY) == len(templates) + 1

    def test_visual_templates(self) -> None:
        """测试图文笔记模板."""
        visual = get_visual_templates()
        assert all(t.is_visual for t in visual)
        assert len(visual) > 0

    def test_text_templates(self) -> None:
        """测试文字笔记模板."""
        text = get_text_templates()
        assert all(not t.is_visual for t in text)
        assert len(text) > 0

    def test_visual_and_text_are_disjoint(self) -> None:
        """测试图文和文字模板不重叠."""
        visual = get_visual_templates()
        text = get_text_templates()
        visual_aliases = {t.alias for t in visual}
        text_aliases = {t.alias for t in text}
        assert not visual_aliases & text_aliases


class TestContentFeatures:
    """内容特征模型测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        features = ContentFeatures()
        assert features.time_line_density == 0.0
        assert features.data_density == 0.0
        assert features.concept_density == 0.0
        assert features.narrative_density == 0.0
        assert features.emotional_density == 0.0
        assert features.text_length == 0
        assert features.confidence == 0.0

    def test_value_ranges(self) -> None:
        """测试值范围约束."""
        features = ContentFeatures(
            time_line_density=0.5,
            data_density=0.8,
            confidence=0.9,
            text_length=1000,
        )
        assert 0.0 <= features.time_line_density <= 1.0
        assert 0.0 <= features.data_density <= 1.0
        assert 0.0 <= features.confidence <= 1.0
        assert features.text_length >= 0
