"""测试新模板效果的脚本."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from core.content_processor import ContentProcessor
from models.transcript import Transcript, TranscriptSegment
from utils import configure_logging, get_logger

configure_logging('INFO')
logger = get_logger(__name__)


class TestTranscriptData:
    """测试数据容器."""
    def __init__(
        self,
        title: str,
        theme: str,
        key_points: list[str],
        quotes: list[str],
        summary: str,
    ):
        self.episode_title = title
        self.theme = theme
        self.key_points = key_points
        self.quotes = quotes
        self.full_text = summary
        self.language = "zh"
        self.duration_seconds = 3600.0


def create_test_transcript(
    title: str,
    theme: str,
    key_points: list[str],
    quotes: list[str],
    summary: str,
) -> TestTranscriptData:
    """创建测试用的转录文本."""
    return TestTranscriptData(
        title=title,
        theme=theme,
        key_points=key_points,
        quotes=quotes,
        summary=summary,
    )


# 测试用例 1: 投资理财类（资产配置）
test_case_1 = create_test_transcript(
    title="资产配置与有效前沿",
    theme="投资理财",
    key_points=[
        "资产配置的核心是找到风险和收益的平衡点",
        "有效前沿理论：在给定风险下追求最大收益",
        "分散投资可以降低非系统性风险",
        "不同资产类别的相关性影响组合效果",
        "定期再平衡是维持目标配置的关键",
    ],
    quotes=[
        "投资不是预测未来，而是管理风险",
        "不要把所有鸡蛋放在一个篮子里",
    ],
    summary="""
    本期播客邀请了资深投资顾问，深入讲解了资产配置的核心理念。
    从有效前沿理论出发，解释了如何在风险和收益之间找到最优平衡点。
    强调了分散投资的重要性，以及不同资产类别之间的相关性对投资组合的影响。
    """,
)

# 测试用例 2: 职场成长类
test_case_2 = create_test_transcript(
    title="35岁职场危机：是坎还是转机",
    theme="职场成长",
    key_points=[
        "35岁危机的本质是能力模型与市场需求的错配",
        "持续学习是应对变化的唯一方法",
        "建立个人品牌和影响力比职位更重要",
        "转型需要提前规划和准备",
    ],
    quotes=[
        "危机就是转机，关键看你如何准备",
        "你的价值不取决于职位，而取决于你能解决的问题",
    ],
    summary="""
    本期播客探讨了35岁职场危机现象，分析了其背后的深层原因。
    嘉宾分享了自己从互联网大厂转型创业的经历，强调了持续学习和
    个人品牌建设的重要性。认为所谓的危机其实是能力模型与市场需求
    错配的体现，提前规划和主动转型是应对之道。
    """,
)

# 测试用例 3: 情感关系类
test_case_3 = create_test_transcript(
    title="亲密关系中的沟通陷阱",
    theme="情感关系",
    key_points=[
        "指责式沟通会让对方进入防御模式",
        "非暴力沟通的四个步骤：观察、感受、需要、请求",
        "情绪失控时先暂停，不要急于表达",
        "倾听比表达更重要",
    ],
    quotes=[
        "沟通的目的不是赢，而是理解",
        "当你说'你总是'的时候，对方就已经听不进去了",
    ],
    summary="""
    本期播客邀请了心理咨询师，讲解了亲密关系中的常见沟通陷阱。
    分析了指责式沟通、冷战、过度理性等问题的根源，介绍了非暴力沟通的
    方法论。强调情绪管理和倾听能力在关系维护中的核心作用。
    """,
)

# 测试用例 4: 科技前沿类
test_case_4 = create_test_transcript(
    title="AI时代，普通人如何不被淘汰",
    theme="科技趋势",
    key_points=[
        "AI不会取代人类，但会取代不会使用AI的人",
        "培养AI无法替代的能力：创造力、同理心、复杂决策",
        "学习使用AI工具提升效率",
        "关注AI伦理和社会影响",
    ],
    quotes=[
        "未来属于会与AI协作的人",
        "技术本身没有善恶，关键看如何使用",
    ],
    summary="""
    本期播客邀请了AI领域专家，探讨了人工智能对普通人工作和生活的影响。
    分析了哪些工作容易被AI替代，哪些能力会越来越重要。建议普通人
    主动学习AI工具，培养创造力、同理心等AI难以替代的能力。
    """,
)

# 测试用例 5: 生活方式类
test_case_5 = create_test_transcript(
    title="极简生活：少即是多",
    theme="生活方式",
    key_points=[
        "极简不是苦行，而是专注于真正重要的事",
        "物质减法带来精神加法",
        "断舍离的三个维度：物品、关系、信息",
        "极简是一种工具，不是目的",
    ],
    quotes=[
        "你占有的东西，同时也在占有你",
        "极简的本质是自由",
    ],
    summary="""
    本期播客分享了极简生活的理念和实践方法。从物品整理延伸到
    人际关系和信息管理，探讨了"少即是多"的生活哲学。强调
    极简不是苦行僧式的生活，而是通过减少干扰来专注于真正重要的事。
    """,
)

# 测试用例 6: 心理健康类
test_case_6 = create_test_transcript(
    title="焦虑时代，如何建立心理韧性",
    theme="心理健康",
    key_points=[
        "焦虑是正常的情绪，不是问题",
        "心理韧性可以通过练习增强",
        "正念冥想是有效的焦虑管理工具",
        "建立支持系统比独自承受更重要",
    ],
    quotes=[
        "焦虑是对未来的过度关注，抑郁是对过去的过度纠结",
        "接纳情绪，而不是对抗情绪",
    ],
    summary="""
    本期播客邀请了临床心理学家，讲解了焦虑情绪的成因和应对方法。
    介绍了心理韧性的概念和培养方法，分享了正念冥想等实用工具。
    强调寻求专业帮助和建立社会支持系统的重要性。
    """,
)

# 测试用例 7: 创业商业类
test_case_7 = create_test_transcript(
    title="从0到1：创业避坑指南",
    theme="创业商业",
    key_points=[
        "创业前验证需求，不要自嗨",
        "现金流是创业公司的生命线",
        "团队比idea更重要",
        "快速迭代，小步快跑",
    ],
    quotes=[
        "创业是九死一生，但失败是最好的老师",
        "不要追求完美，要追求验证",
    ],
    summary="""
    本期播客邀请了连续创业者，分享了从0到1的创业经验和教训。
    讲解了需求验证、团队组建、融资策略等关键环节，分析了常见
    的创业陷阱和避坑方法。强调快速验证和迭代的重要性。
    """,
)

# 测试用例 8: 教育学习类
test_case_8 = create_test_transcript(
    title="高效学习法：如何真正学会一件事",
    theme="教育学习",
    key_points=[
        "被动学习效率低，主动回忆效果更好",
        "间隔重复是记忆的关键",
        "教别人是最好的学习方式",
        "建立知识网络，而非孤立记忆",
    ],
    quotes=[
        "学习不是输入，而是输出",
        "理解一件事的标准是你能用自己的话讲清楚",
    ],
    summary="""
    本期播客邀请了认知科学家，讲解了高效学习的原理和方法。
    分析了被动阅读和主动回忆的效果差异，介绍了间隔重复、费曼技巧
    等实用方法。强调建立知识体系而非孤立记忆的重要性。
    """,
)

# 测试用例 9: 文化历史类
test_case_9 = create_test_transcript(
    title="宋朝人的一天：穿越千年的生活智慧",
    theme="文化历史",
    key_points=[
        "宋朝是中华文明的高峰，生活美学发达",
        "点茶、插花、焚香、挂画是宋人四雅",
        "宋朝商业繁荣，市民文化兴起",
        "宋人的生活态度值得现代人借鉴",
    ],
    quotes=[
        "宋人的生活，是审美化的日常",
        "在快节奏的今天，宋人的慢生活是一种启示",
    ],
    summary="""
    本期播客通过历史学者的讲述，还原了宋朝人的日常生活。
    从饮食起居到文化娱乐，展现了宋朝高度发达的生活美学和
    商业文明。探讨了宋人生活智慧对现代人的启示意义。
    """,
)

# 测试用例 10: 健康养生类
test_case_10 = create_test_transcript(
    title="睡眠革命：为什么你总是睡不醒",
    theme="健康养生",
    key_points=[
        "睡眠质量比时长更重要",
        "褪黑素不是安眠药，不能滥用",
        "睡前蓝光暴露影响入睡",
        "建立固定的睡眠节律很关键",
    ],
    quotes=[
        "睡眠是身体的自我修复时间",
        "熬夜的代价，远比你想象的大",
    ],
    summary="""
    本期播客邀请了睡眠医学专家，讲解了睡眠的科学原理和改善方法。
    分析了现代人常见的睡眠问题及其成因，介绍了睡眠卫生、认知行为疗法
    等改善方法。强调建立健康睡眠习惯的重要性。
    """,
)


def test_template_loading():
    """测试模板加载功能."""
    print("=" * 60)
    print("测试 1: 模板加载")
    print("=" * 60)

    from jinja2 import Environment, FileSystemLoader
    
    prompts_dir = Path("./prompts")
    available_templates = {
        "v1": "xiaohongshu_note_v1",
        "v2": "xiaohongshu_note_v2",
        "v3": "xiaohongshu_note_v3",
        "v4": "xiaohongshu_note_v4_humanized",
        "v5": "xiaohongshu_note_v5_dry_goods",
        "v6": "xiaohongshu_note_v6_story",
    }

    templates_to_test = ["v1", "v2", "v3", "v4", "v5", "v6"]

    for template in templates_to_test:
        try:
            template_path = prompts_dir / f"{available_templates.get(template, template)}.md"
            if template_path.exists():
                print(f"✅ 模板 {template}: 已找到 ({template_path.name})")
            else:
                print(f"❌ 模板 {template}: 文件不存在")
        except Exception as e:
            print(f"❌ 模板 {template}: 错误 - {e}")


def test_ai_marker_detection():
    """测试AI感检测功能."""
    print("\n" + "=" * 60)
    print("测试 2: AI感检测")
    print("=" * 60)

    # 内联AI标记检测逻辑，避免依赖ContentProcessor
    def detect_ai_markers(content: str) -> list[str]:
        markers = []
        mechanical_words = ["首先", "其次", "最后", "综上所述", "值得注意的是", "总而言之"]
        for word in mechanical_words:
            if word in content:
                markers.append(word)
        absolute_words = ["无敌", "闭眼入", "必看", "绝对", "一定", "必然"]
        for word in absolute_words:
            if word in content:
                markers.append(word)
        lines = content.split("\n")
        for i in range(len(lines) - 2):
            if all("。" in line for line in lines[i:i+3]):
                prefixes = [line[:3] for line in lines[i:i+3]]
                if len(set(prefixes)) < 3:
                    markers.append("排比句")
                    break
        return markers

    test_contents = [
        ("高AI感文本", """
        首先，我们需要了解资产配置的重要性。其次，分散投资可以降低风险。
        最后，定期再平衡是维持目标配置的关键。综上所述，投资不是预测未来，而是管理风险。
        值得注意的是，不要把所有鸡蛋放在一个篮子里。这绝对是必看的投资指南！
        """),
        ("低AI感文本", """
        说实话，我之前对资产配置一窍不通，直到听了这期播客才有点明白。
        让我印象最深刻的是那句"投资不是预测未来，而是管理风险"——
        当时我就愣住了，这不就是我一直以来的误区吗？
        你有没有想过，为什么我们总是想预测市场？
        """),
        ("中等AI感文本", """
        听完这期播客，我学到了三个要点。第一，资产配置很重要。
        第二，分散投资可以降低风险。第三，定期再平衡很关键。
        不过说实话，有些部分我没太听懂，但大意是明白了。
        """),
    ]

    for name, content in test_contents:
        markers = detect_ai_markers(content)
        status = "❌ 检测到AI标记" if markers else "✅ 无AI标记"
        print(f"\n{name}: {status}")
        if markers:
            print(f"  标记: {', '.join(markers)}")


def test_prompt_rendering():
    """测试Prompt模板渲染."""
    print("\n" + "=" * 60)
    print("测试 3: Prompt模板渲染")
    print("=" * 60)

    from jinja2 import Environment, FileSystemLoader

    prompts_dir = Path("./prompts")
    env = Environment(loader=FileSystemLoader(prompts_dir))

    available_templates = {
        "v4": "xiaohongshu_note_v4_humanized",
        "v5": "xiaohongshu_note_v5_dry_goods",
        "v6": "xiaohongshu_note_v6_story",
    }

    test_cases = [
        ("投资理财", test_case_1),
        ("职场成长", test_case_2),
        ("情感关系", test_case_3),
    ]

    templates = ["v4", "v5", "v6"]

    for category, transcript in test_cases:
        print(f"\n--- {category} ---")
        for template in templates:
            try:
                template_obj = env.get_template(f"{available_templates[template]}.md")
                prompt = template_obj.render(
                    podcast_title="测试播客",
                    episode_title=transcript.episode_title,
                    theme=transcript.theme,
                    key_points=transcript.key_points,
                    quotes=transcript.quotes,
                    transcript_summary=transcript.full_text[:500],
                    tags=["测试标签1", "测试标签2", "测试标签3"],
                )

                has_role = "System Instruction" in prompt or "Role" in prompt
                has_constraints = "Constraints" in prompt or "约束" in prompt
                has_input = "Input" in prompt or "输入" in prompt

                status = "✅" if all([has_role, has_constraints, has_input]) else "⚠️"
                print(f"  {status} 模板 {template}: 长度 {len(prompt)} 字符")

                if category == "投资理财" and template == "v4":
                    example_path = Path("./data/test_prompt_example.md")
                    example_path.parent.mkdir(parents=True, exist_ok=True)
                    example_path.write_text(prompt, encoding="utf-8")
                    print(f"    示例已保存到: {example_path}")

            except Exception as e:
                print(f"  ❌ 模板 {template}: 错误 - {e}")


def test_full_pipeline_mock():
    """测试完整流程（模拟LLM响应）."""
    print("\n" + "=" * 60)
    print("测试 4: 完整流程（模拟）")
    print("=" * 60)

    # 内联AI标记检测逻辑
    def detect_ai_markers(content: str) -> list[str]:
        markers = []
        mechanical_words = ["首先", "其次", "最后", "综上所述", "值得注意的是", "总而言之"]
        for word in mechanical_words:
            if word in content:
                markers.append(word)
        absolute_words = ["无敌", "闭眼入", "必看", "绝对", "一定", "必然"]
        for word in absolute_words:
            if word in content:
                markers.append(word)
        lines = content.split("\n")
        for i in range(len(lines) - 2):
            if all("。" in line for line in lines[i:i+3]):
                prefixes = [line[:3] for line in lines[i:i+3]]
                if len(set(prefixes)) < 3:
                    markers.append("排比句")
                    break
        return markers

    # 模拟LLM生成的不同风格文本
    mock_outputs = {
        "v4": """
# 听完这期播客，我终于搞懂了资产配置

🎙️ 听完播客《测试播客》的资产配置与有效前沿，想和你聊聊我的感受

早上通勤路上听完了这期，说实话一开始有点懵，但越听越有意思。

让我印象最深刻的是那句"投资不是预测未来，而是管理风险"——
我当时就想，这不就是我一直以来的误区吗？总想着预测市场涨跌。

还有一个点让我挺意外的：原来分散投资不只是多买几只股票，
而是要考虑不同资产之间的相关性。这个我之前真的没意识到。

听完这期，我最大的感受是：投资其实是一门关于控制的学问，
控制你能控制的，接受你不能控制的。

你们有听这期吗？对资产配置怎么看？👇

#投资理财 #资产配置 #播客笔记 #个人成长
        """,
        "v5": """
# 3分钟搞懂资产配置：终于有人说明白了

🎙️ 内容来源：播客《测试播客》— 资产配置与有效前沿

说实话，我一直搞不太懂资产配置到底在配什么...

直到听了这期，我才搞明白：

💡 核心逻辑：风险和收益的平衡游戏
就像走钢丝，左边是风险，右边是收益，
资产配置就是找到那个让你不摔下来的平衡点。

💡 有效前沿：最优解的集合
想象一张地图，上面有一条线，线上的每个点都是
"同样风险下收益最高"或"同样收益下风险最低"的组合。

💡 分散投资：不是数量多，而是相关性低
买10只科技股不叫分散，买股票+债券+黄金才叫分散。

如果你也想了解投资，推荐去听原播客！

#投资理财 #资产配置 #干货分享 #知识科普
        """,
        "v6": """
# 听完这期播客，我做出了一个决定

🎙️ 听完播客《测试播客》的资产配置与有效前沿，有些话想对你说

上周的一个晚上，我加班到十点，躺在床上刷手机，
突然看到账户里的理财收益，心里一阵失落——
明明买了那么多"理财产品"，为什么收益还是这么差？

这让我想起播客里说的：

"投资不是预测未来，而是管理风险"

我突然意识到，我一直在做的不是投资，是赌博。
赌哪只股票会涨，赌哪个基金经理靠谱。

现在的我，开始认真学习资产配置了。
不是为了暴富，是为了让辛苦赚的钱，能安稳地增长。

如果你也在为理财焦虑，不妨听听这期播客。

#投资理财 #资产配置 #成长感悟 #播客推荐
        """,
    }

    for template, mock_content in mock_outputs.items():
        print(f"\n--- 模板 {template} ---")

        # 检测AI标记
        ai_markers = detect_ai_markers(mock_content)

        if ai_markers:
            print(f"⚠️ 检测到AI标记: {', '.join(ai_markers)}")
        else:
            print("✅ 无AI标记，通过检测")

        # 统计字数
        word_count = len(mock_content.replace(" ", "").replace("\n", ""))
        print(f"  字数: {word_count}")

        # 检查结构元素
        has_interaction = "?" in mock_content or "？" in mock_content
        has_personal = "我" in mock_content or "我的" in mock_content
        has_emoji = any(e in mock_content for e in ["🎙️", "💡", "👇"])

        print(f"  互动元素: {'✅' if has_interaction else '❌'}")
        print(f"  个人视角: {'✅' if has_personal else '❌'}")
        print(f"  视觉标记: {'✅' if has_emoji else '❌'}")


def run_tests():
    """运行所有测试."""
    print("\n" + "=" * 60)
    print("小红书笔记模板测试报告")
    print("=" * 60)

    test_template_loading()
    test_ai_marker_detection()
    test_prompt_rendering()
    test_full_pipeline_mock()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
