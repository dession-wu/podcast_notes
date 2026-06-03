# 播客笔记项目 — UI 设计规范文档

## 一、项目概述

**产品名称**：播客笔记 — 自动化内容提炼工具  
**核心功能**：播客音频 → 语音转文字 → AI 内容提炼 → 小红书图文发布  
**目标用户**：内容创作者、知识博主、播客听众  
**设计目标**：提升视觉品质与品牌一致性，建立可扩展的设计系统

---

## 二、设计系统架构

### 2.1 Token 三层架构

```
Primitive (原始值)
    ↓
Semantic (语义层)
    ↓
Component (组件层)
```

**文件位置**：`templates/styles/design-tokens.css`

### 2.2 三种视觉风格

| 风格 | 定位 | 适用场景 |
|------|------|---------|
| **极简知识感** (Minimal) | 干净留白、精致排版、低饱和 | 知识类、商业类播客 |
| **活力社交感** (Vibrant) | 明亮色彩、圆角卡片、emoji | 轻松娱乐、生活方式类 |
| **高级杂志感** (Editorial) | 大字号标题、强对比、serif字体 | 深度访谈、投资商业类 |

---

## 三、色彩系统

### 3.1 极简知识感 (Minimal)

```css
--s-primary: #1e293b;        /* 深 slate */
--s-primary-light: #334155;
--s-accent: #d97706;         /* 琥珀金 */
--s-bg: #fafaf9;             /* 暖白 */
--s-bg-elevated: #ffffff;
--s-text-primary: #1c1917;
--s-text-secondary: #57534e;
--s-text-tertiary: #a8a29e;
--s-highlight: #fef3c7;
```

### 3.2 活力社交感 (Vibrant)

```css
--s-primary: #ec4899;        /* 粉红 */
--s-secondary: #8b5cf6;      /* 紫色 */
--s-accent: #f59e0b;         /* 琥珀 */
--s-bg: #fff1f2;             /* 极浅粉 */
--s-bg-elevated: #ffffff;
--s-text-primary: #881337;
--s-text-secondary: #be185d;
--s-highlight: #fef08a;
```

### 3.3 高级杂志感 (Editorial)

```css
--s-primary: #0f172a;        /* 近黑 */
--s-secondary: #64748b;
--s-accent: #dc2626;         /* 红 */
--s-bg: #f8fafc;
--s-bg-elevated: #ffffff;
--s-text-primary: #0f172a;
--s-text-secondary: #475569;
--s-highlight: #fee2e2;
```

### 3.4 中性色阶（全局通用）

| Token | 值 | 用途 |
|-------|-----|------|
| --p-white | #ffffff | 纯白背景 |
| --p-gray-50 | #fafafa | 极浅灰背景 |
| --p-gray-100 | #f5f5f5 | 卡片背景 |
| --p-gray-200 | #e5e5e5 | 边框 |
| --p-gray-400 | #a3a3a3 | 禁用文字 |
| --p-gray-600 | #525252 | 次要文字 |
| --p-gray-900 | #171717 | 主要文字 |

---

## 四、排版系统

### 4.1 字体选择

| 风格 | 标题字体 | 正文字体 | 说明 |
|------|---------|---------|------|
| Minimal | Noto Sans SC (900) | Noto Sans SC (400) | 统一无衬线，简洁 |
| Vibrant | Noto Sans SC (900) | Noto Sans SC (400) | 统一无衬线，活泼 |
| Editorial | Noto Serif SC (900) | Noto Serif SC (400) | 衬线标题，杂志感 |

### 4.2 字号层级

| Token | 值 | 用途 |
|-------|-----|------|
| --p-text-xs | 12px | 标签、脚注 |
| --p-text-sm | 14px | 辅助文字 |
| --p-text-base | 16px | 正文 |
| --p-text-lg | 18px | 引言、强调 |
| --p-text-xl | 20px | 小标题 |
| --p-text-2xl | 24px | 章节标题 |
| --p-text-3xl | 30px | 页面标题 |
| --p-text-4xl | 36px | 大标题 |
| --p-text-5xl | 48px | 封面主标题 |

### 4.3 行高规范

| Token | 值 | 用途 |
|-------|-----|------|
| --p-leading-tight | 1.25 | 大标题 |
| --p-leading-snug | 1.375 | 小标题 |
| --p-leading-normal | 1.5 | 正文 |
| --p-leading-relaxed | 1.625 | 长文本 |

---

## 五、间距系统

基于 4px 基数（4pt grid）：

| Token | 值 | 用途 |
|-------|-----|------|
| --p-space-1 | 4px | 极小间距 |
| --p-space-2 | 8px | 紧凑间距 |
| --p-space-3 | 12px | 组件内间距 |
| --p-space-4 | 16px | 标准间距 |
| --p-space-5 | 20px | 卡片内边距 |
| --p-space-6 | 24px | 区块间距 |
| --p-space-8 | 32px | 大区块间距 |
| --p-space-10 | 40px | 页面边距 |
| --p-space-12 | 48px | 大间距 |

---

## 六、组件设计

### 6.1 按钮

**Primary Button**
- 背景：var(--s-primary)
- 文字：白色
- 圆角：var(--p-radius-md) / var(--p-radius-full) / 0（按风格）
- 内边距：px-5 py-2.5
- Hover：亮度提升 10%

**Secondary Button**
- 背景：透明 / var(--s-bg-subtle)
- 文字：var(--s-primary)
- 边框：1px solid var(--s-border) / 2px solid var(--s-primary)

### 6.2 卡片

| 风格 | 圆角 | 阴影 | 边框 |
|------|------|------|------|
| Minimal | 12px | sm | 1px subtle |
| Vibrant | 20px | md | 1.5px |
| Editorial | 0 | none | 2px solid |

### 6.3 输入框

- 背景：var(--s-bg-elevated)
- 边框：1px solid var(--s-border)
- 圆角：按风格（md / lg / 0）
- Focus：border-color → var(--s-primary) / var(--s-accent)
- 内边距：px-4 py-3

### 6.4 标签 (Tag)

| 风格 | 背景 | 文字 | 圆角 |
|------|------|------|------|
| Minimal | bg-subtle | text-secondary | full |
| Vibrant | primary-light | text-inverse | full |
| Editorial | primary | text-inverse | 0 |

---

## 七、页面布局规范

### 7.1 小红书竖图尺寸

- **画布尺寸**：900px × 1200px（3:4 比例）
- **安全边距**：左右 60px，上下 40px
- **内容区域**：780px × 1120px

### 7.2 Web 管理后台布局

- **最大宽度**：max-w-6xl (1152px)
- **页面边距**：px-4 sm:px-6 lg:px-8
- **卡片间距**：gap-4 / gap-6
- **响应式断点**：sm(640px), md(768px), lg(1024px), xl(1280px)

---

## 八、交互动效

### 8.1 动画时长

| 场景 | 时长 | Easing |
|------|------|--------|
| 微交互（hover） | 150ms | ease-out |
| 页面切换 | 250ms | cubic-bezier(0.16, 1, 0.3, 1) |
| 复杂过渡 | 400ms | cubic-bezier(0.65, 0, 0.35, 1) |

### 8.2 常用动效

- **Fade In**：opacity 0→1 + translateY(8px→0)
- **Slide In**：opacity 0→1 + translateX(-12px→0)
- **Progress Bar**：width 动画，ease-out
- **Card Hover**：scale(1.02) + shadow 增强

### 8.3 原则

- 动画必须表达因果关系，不做纯装饰
- 支持 prefers-reduced-motion
- 所有交互元素在 100ms 内给出反馈

---

## 九、响应式适配

### 9.1 断点定义

| 断点 | 宽度 | 设备 |
|------|------|------|
| sm | 640px | 大手机 |
| md | 768px | 平板竖屏 |
| lg | 1024px | 平板横屏 / 小桌面 |
| xl | 1280px | 桌面 |

### 9.2 适配策略

**小红书竖图**：固定 900×1200px，不响应式（输出图片）

**Web 后台**：
- Mobile First 设计
- 网格：1 col → 2 col → 3 col
- 导航：底部标签栏（移动端）/ 顶部导航（桌面端）
- 字体：最小 16px（避免 iOS 自动缩放）

---

## 十、文件结构

```
templates/
├── styles/
│   └── design-tokens.css          # 设计 Token 系统
├── minimal/                        # 风格 A
│   ├── cover.html
│   ├── content.html
│   └── summary.html
├── vibrant/                        # 风格 B
│   ├── cover.html
│   ├── content.html
│   └── summary.html
├── editorial/                      # 风格 C
│   ├── cover.html
│   ├── content.html
│   └── summary.html
├── previews/                       # 示例图片
├── demo_data.json                  # 演示数据
└── generate_previews.py            # 生成脚本

web-dashboard/                      # Web 管理后台
├── src/
│   └── app/
│       ├── layout.tsx
│       ├── page.tsx
│       └── globals.css
├── next.config.ts
└── package.json
```

---

## 十一、开发实现指南

### 11.1 使用 Token

所有颜色、间距、圆角必须使用 CSS Variable，禁止硬编码：

```css
/* 正确 */
background: var(--s-bg);
color: var(--s-text-primary);
padding: var(--p-space-4);

/* 错误 */
background: #fafaf9;
color: #171717;
padding: 16px;
```

### 11.2 切换风格

在 HTML 根元素上设置 `data-theme` 属性：

```html
<body data-theme="minimal">  <!-- 或 vibrant / editorial -->
```

### 11.3 模板变量

所有模板使用 Jinja2 语法，保持与现有后端兼容：

```html
<h1>{{ title }}</h1>
{% for point in key_points %}
  <p>{{ point.title }}</p>
{% endfor %}
```

### 11.4 截图生成

使用 Playwright 将 HTML 渲染为 900×1200 PNG：

```python
page = await browser.new_page(viewport={"width": 900, "height": 1200})
await page.set_content(html)
await page.screenshot(path="output.png")
```

---

## 十二、示例预览

三种风格的封面页和内容页示例已生成至 `templates/previews/` 目录：

| 文件 | 说明 |
|------|------|
| minimal_cover.png | 极简风格封面 |
| minimal_content.png | 极简风格内容页 |
| minimal_summary.png | 极简风格总结页 |
| vibrant_cover.png | 活力风格封面 |
| vibrant_content.png | 活力风格内容页 |
| vibrant_summary.png | 活力风格总结页 |
| editorial_cover.png | 杂志风格封面 |
| editorial_content.png | 杂志风格内容页 |
| editorial_summary.png | 杂志风格总结页 |

---

*文档版本：v1.0*  
*更新日期：2026-05-26*
