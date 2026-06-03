# 播客笔记项目 UI 设计方案计划

## 项目背景

播客转小红书自动化工作流 —— 从播客音频抓取 → 语音转文字 → AI 内容提炼 → 小红书图文发布的端到端自动化工具。

当前已有：
- Python 后端处理流程（音频下载、转录、内容提炼、笔记生成）
- HTML 模板系统（Jinja2）生成小红书竖图（900×1200px）
- Playwright 截图生成 PNG
- 3 种配色方案（blue/green/purple）
- 多个模板：cover.html, content.html, summary.html, content_detailed.html, content_transcript.html 等

## 用户需求

1. **小红书图文输出模板** — 三种风格方向供选择：
   - 极简知识感（干净留白、精致排版、低饱和色彩）
   - 活力社交感（明亮色彩、圆角卡片、emoji 点缀）
   - 高级杂志感（大字号标题、强对比排版、editorial 风格）

2. **Web 管理后台** — React + Tailwind CSS，轻量操作面板：
   - 上传音频 / RSS 订阅源
   - 选择模板和风格
   - 查看处理进度
   - 预览和下载生成的图文
   - 历史笔记库（基础版）

## 设计范围

### A. 小红书图文模板 redesign（三种风格）

每个风格包含：
- 封面页（cover）
- 内容页（content / content_detailed）
- 总结页（summary）
- 文字稿页（content_transcript）

### B. Web 管理后台 UI

页面：
1. 登录页
2. 仪表盘首页（上传入口 + 最近任务）
3. 任务处理页（进度展示）
4. 笔记库（历史记录列表 + 预览）
5. 笔记详情页（多图预览 + 下载）

## 技术栈

- **图文模板**：HTML + CSS（Jinja2 模板），Playwright 截图
- **Web 后台**：React 18 + Tailwind CSS + shadcn/ui
- **设计 Token**：CSS Variables 三层架构（Primitive → Semantic → Component）

## 实施步骤

### Phase 1: 设计系统搭建
1. 定义三层 Token 架构（色彩、排版、间距、阴影）
2. 创建三种风格的配色方案
3. 定义字体层级和排版规范

### Phase 2: 小红书图文模板（三种风格）
1. 风格 A：极简知识感 — 重新设计所有 HTML 模板
2. 风格 B：活力社交感 — 重新设计所有 HTML 模板
3. 风格 C：高级杂志感 — 重新设计所有 HTML 模板
4. 每种风格生成示例图片供用户比较

### Phase 3: Web 管理后台
1. 搭建 React + Tailwind 项目结构
2. 实现登录页
3. 实现仪表盘首页
4. 实现任务处理页（进度展示）
5. 实现笔记库列表页
6. 实现笔记详情页（多图预览）
7. 响应式适配（移动端、平板、桌面端）

### Phase 4: 设计规范文档
1. 编写完整的设计规范文档（色彩、排版、组件、布局、动效）
2. 编写开发实现指南

## 交付物

1. 三种风格的 HTML 模板文件
2. Web 管理后台 React 代码
3. 设计规范文档（Markdown）
4. 示例图片（每种风格各一套）

## 注意事项

- 小红书竖图尺寸保持 900×1200px
- 所有模板使用 Jinja2 语法，保持与现有后端兼容
- Web 后台需要与现有 Python API 对接（预留接口）
- 确保中文字体加载和渲染质量
