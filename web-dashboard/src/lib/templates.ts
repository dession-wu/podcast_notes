/**
 * 笔记模板注册表 — 与后端 core/template_recommender.py 的 TEMPLATE_REGISTRY 对齐.
 *
 * 提供模板元数据查询与分类过滤能力，供 TemplateSelector / SmartRecommendation 使用。
 */

export interface TemplateMetadata {
  /** 模板别名（如 v9） */
  alias: string;
  /** 人话名称（如 深度分析型） */
  name: string;
  /** 一句话描述模板特点 */
  description: string;
  /** 模板分类 */
  category: "图文笔记" | "文字笔记";
  /** 适用场景标签 */
  tags: string[];
  /** 输出格式 */
  output_format: string;
  /** 是否生成图文 */
  is_visual: boolean;
}

/** 全部模板注册表（与后端保持一致） */
export const TEMPLATE_REGISTRY: TemplateMetadata[] = [
  {
    alias: "v9",
    name: "深度分析型",
    description: "时间线+阶段划分+标签化，信息密度最高",
    category: "图文笔记",
    tags: ["商业", "历史", "投资", "深度访谈"],
    output_format: "stages_json",
    is_visual: true,
  },
  {
    alias: "v8",
    name: "凝练文稿型",
    description: "忠于播客原结构，删减口语化内容",
    category: "图文笔记",
    tags: ["对话", "访谈", "纪实"],
    output_format: "sections_json",
    is_visual: true,
  },
  {
    alias: "v7",
    name: "知识翻译官",
    description: "用生活类比解释专业概念",
    category: "图文笔记",
    tags: ["科普", "方法论", "概念解读"],
    output_format: "key_points_json",
    is_visual: true,
  },
  {
    alias: "v7d",
    name: "图文高密度型",
    description: "信息密度更高的图文排版",
    category: "图文笔记",
    tags: ["内容量大", "信息密集"],
    output_format: "key_points_json",
    is_visual: true,
  },
  {
    alias: "v6",
    name: "故事共鸣型",
    description: "叙事驱动，强调情感共鸣",
    category: "文字笔记",
    tags: ["个人成长", "情感", "故事"],
    output_format: "text",
    is_visual: false,
  },
  {
    alias: "v5",
    name: "干货清单型",
    description: "条目化呈现，actionable",
    category: "文字笔记",
    tags: ["技巧", "工具", "清单"],
    output_format: "text",
    is_visual: false,
  },
  {
    alias: "v4",
    name: "真人笔记型",
    description: "降低 AI 感，像真人手写",
    category: "文字笔记",
    tags: ["追求真实感", "去 AI 化"],
    output_format: "text",
    is_visual: false,
  },
  {
    alias: "v3",
    name: "故事共鸣型（经典）",
    description: "情感驱动、引发共鸣",
    category: "文字笔记",
    tags: ["生活", "情感类"],
    output_format: "text",
    is_visual: false,
  },
  {
    alias: "v2",
    name: "深度干货型（经典）",
    description: "知识密集、逻辑严密",
    category: "文字笔记",
    tags: ["商业", "科技", "理财"],
    output_format: "text",
    is_visual: false,
  },
  {
    alias: "v1",
    name: "标准型（经典）",
    description: "平衡信息量与可读性",
    category: "文字笔记",
    tags: ["通用场景"],
    output_format: "text",
    is_visual: false,
  },
];

/** 图文类模板（生成配图） */
export const VISUAL_TEMPLATES: TemplateMetadata[] = TEMPLATE_REGISTRY.filter(
  (t) => t.is_visual
);

/** 文字类模板 */
export const TEXT_TEMPLATES: TemplateMetadata[] = TEMPLATE_REGISTRY.filter(
  (t) => !t.is_visual
);

/** 模板别名 → 完整模板名映射（与后端 process.py 的 _TEMPLATE_MAP 一致） */
const FULL_NAME_MAP: Record<string, string> = {
  v1: "xiaohongshu_note_v1",
  v2: "xiaohongshu_note_v2",
  v3: "xiaohongshu_note_v3",
  v4: "xiaohongshu_note_v4_humanized",
  v5: "xiaohongshu_note_v5_dry_goods",
  v6: "xiaohongshu_note_v6_story",
  v7: "xiaohongshu_note_v7_visual",
  v7d: "xiaohongshu_note_v7_visual_dense",
  v8: "xiaohongshu_note_v8_transcript",
  v9: "xiaohongshu_note_v9_analysis",
};

/** 完整模板名 → 别名反查映射 */
const ALIAS_BY_FULL_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(FULL_NAME_MAP).map(([alias, fullName]) => [fullName, alias])
);

/**
 * 按别名（如 "v9"）查找模板元数据.
 *
 * @returns 匹配的模板；未找到时返回 undefined
 */
export function getTemplateByAlias(alias: string): TemplateMetadata | undefined {
  return TEMPLATE_REGISTRY.find((t) => t.alias === alias);
}

/**
 * 获取模板的展示名称.
 *
 * 兼容两种输入：
 * - 别名（如 "v9"）→ 返回人话名称（如 "深度分析型"）
 * - 完整模板名（如 "xiaohongshu_note_v9_analysis"）→ 先反查别名再取人话名称
 *
 * 无法识别时原样返回输入，避免 UI 显示空白。
 */
export function getTemplateName(aliasOrFullName: string): string {
  if (!aliasOrFullName) return "";

  const byAlias = getTemplateByAlias(aliasOrFullName);
  if (byAlias) return byAlias.name;

  const alias = ALIAS_BY_FULL_NAME[aliasOrFullName];
  if (alias) {
    const template = getTemplateByAlias(alias);
    if (template) return template.name;
  }

  return aliasOrFullName;
}

/** 获取模板的完整模板名（用于请求后端时的 template 字段） */
export function getTemplateFullName(alias: string): string | undefined {
  return FULL_NAME_MAP[alias];
}