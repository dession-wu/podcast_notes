# 播客笔记 · Podcast Notes

> 把听到的播客，变成可搜索、可下载、可二次创作的知识资产

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

[English](#english) | [简体中文](#简体中文)

---

## 这是什么


https://github.com/user-attachments/assets/3e4602d0-8a19-4ee8-a678-773b6c3d26c7


**播客笔记**是一款把"听完就忘"的播客变成"可检索、可下载、可二次创作"的知识资产的工具。你上传一段音频，它会自动完成：转写 → 内容理解 → 笔记生成 → 图文渲染。

我们不做"全自动流水线"，而是做你的**创作副驾（Copilot）**——AI 出草稿，你来终审。

## 它解决什么问题

- 听完一期 60 分钟的播客，想回头查某句话？不用再拖进度条。
- 想把内容发到小红书/朋友圈？不用手动整理 2-3 小时。
- 听了十几期同类主题想做研究？没有结构化笔记可以检索？
- 自己是内容创作者，播客是优质素材源但处理成本太高？

**播客笔记**把这些事从"几小时"压缩到"几分钟"。

### 效果演示
<img width="677" height="1698" alt="image" src="https://github.com/user-attachments/assets/b37e31c1-709f-4be3-9ac7-8099702484b1" />

---

## 核心特性

### 内容输入
- **本地音频上传**：支持 MP3 / WAV / M4A / AAC / OGG
- **RSS 订阅源解析**：支持小宇宙、Apple Podcasts、通用 RSS
- **音频直链粘贴**：直接粘贴 URL 即可
- **拖拽上传**：拖到上传区立刻解析

### 语音转写
- **多引擎支持**：SenseVoice（中文优化）/ faster-whisper（英文）/ Whisper / ElevenLabs Scribe
- **语言自动检测**：根据音频自动选择引擎和模型
- **说话人识别**：区分"主持人 / 嘉宾 1 / 嘉宾 2"
- **时间戳对齐**：每句话带起止时间，方便回溯
- **文本预处理**：去口头禅（嗯/啊/那个）、合并短句

### 内容理解与笔记生成
- **9 套笔记模板**（v1-v9），覆盖从"通用摘要"到"深度因果分析"：
  - v1 标准型｜v2 深度干货｜v3 故事共鸣
  - v4 真人笔记｜v5 知识翻译官｜v6 故事型
  - v7 图文结构化｜v7d 图文高密度｜v8 播客凝练
  - v9 深度分析（带因果链）
- **自动提炼**：核心观点、关键数据、金句、话题标签
- **来源自动标注**：每篇笔记自动加"内容提炼自 XX 播客 XX 期"

### 图文卡片渲染
- **3 种视觉风格**：极简知识感 / 活力社交感 / 高级杂志感
- **3:4 比例**（900×1200px），直接适配小红书竖图
- **三层 Token 设计系统**：切换风格只改根节点属性
- **批量导出**：封面 + 内容页 + 总结页 + 思考页（v9）

### Web 管理后台
- **搜索与发现**：跨平台搜索播客（PodcastIndex / iTunes / ListenNotes）
- **创建笔记**：上传 → 选模板 → 生成，三步完成
- **我的库**：所有历史笔记的集中管理
- **转录查看器**：带时间戳的全文 + 关键词搜索
- **笔记阅读器**：预览 / 校对 / 下载三合一
- **多 LLM 切换**：OpenAI / Anthropic / Ollama / DeepSeek 等

### 文档下载与校对
- **多格式导出**：TXT / Markdown / JSON / PNG（图片）
- **批量打包**：一键下载为 ZIP
- **AI 校对**：检测语法 / 错别字 / 标点错误，逐条确认是否采纳

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                       Web Dashboard (Next.js)               │
│  搜索 · 创建 · 库 · 转录查看 · 笔记阅读 · 校对 · 下载         │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend (Python)                  │
│  /api/search  /api/transcribe  /api/process  /api/download  │
└────┬─────────────┬─────────────┬──────────────┬─────────────┘
     │             │             │              │
     ▼             ▼             ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│  RSS /  │  │  STT 引擎 │  │   LLM    │  │  模板渲染     │
│  搜索    │  │ SenseVoice│  │ OpenAI / │  │ Jinja2 +     │
│ Podcast │  │ Whisper / │  │ Claude / │  │ Playwright   │
│ Index   │  │ faster-   │  │ Ollama / │  │ HTML → PNG   │
│ iTunes  │  │ whisper   │  │ DeepSeek │  │              │
└─────────┘  └──────────┘  └──────────┘  └──────────────┘
```

---

## 快速开始

> 5 分钟跑起来：上传一个音频文件，得到一篇笔记。

### 方式 A：Docker Compose（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/dession-wu/podcast_notes.git
cd podcast_notes

# 2. 准备环境变量
cp .env.example .env
# 编辑 .env，至少填入一个 LLM 的 API Key

# 3. 启动
docker compose up -d

# 4. 打开浏览器
# 前端：http://localhost:3000
# 后端：http://localhost:8000
# API 文档：http://localhost:8000/docs
```

### 方式 B：本地裸机运行

**环境要求**：Python 3.10+ / Node.js 20+ / FFmpeg

```bash
# 1. 克隆并安装 Python 依赖
git clone https://github.com/dession-wu/podcast_notes.git
cd podcast_notes
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[whisper]"

# 2. 准备环境变量
cp .env.example .env
# 编辑 .env，填入 API Key

# 3. 启动后端（新终端 1）
python -m backend.main
# → http://localhost:8000

# 4. 启动前端（新终端 2）
cd web-dashboard
npm install
npm run dev
# → http://localhost:3000
```

### 方式 C：CLI 脚本（无 UI）

适合批量处理或服务器环境：

```bash
# 从 RSS 处理最新一期
python scripts/download_and_process.py --rss https://example.com/feed.xml

# 处理本地音频
python scripts/download_and_process.py --audio ./podcast_episode.mp3

# 指定模板
python scripts/download_and_process.py --rss <url> --template v9
```

---

## 配置说明

复制 `.env.example` 为 `.env`，按需填入以下配置：

### LLM 提供商（至少填一个）

| 提供商 | 必填变量 | 备注 |
|-------|---------|------|
| **OpenAI** | `OPENAI_API_KEY` | 兼容 DeepSeek / 月之暗面 / 硅基流动 / 通义千问等 |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude 3.5 系列 |
| **Ollama** | `OLLAMA_HOST`, `OLLAMA_MODEL` | 本地运行，完全免费 |

修改 `DEFAULT_LLM_PROVIDER` 切换默认提供商。

### 语音转写引擎

| 引擎 | 配置变量 | 适用场景 |
|-----|---------|---------|
| **SenseVoice** | 默认中文优化，无需 API Key | 中文播客 |
| **faster-whisper** | `FASTER_WHISPER_MODEL` | 英文播客 |
| **Whisper** | `WHISPER_MODEL`, `WHISPER_DEVICE` | 备选 |
| **ElevenLabs Scribe** | `ELEVENLABS_API_KEY` | 云端高精度 |

### 其他可选项

- `LOG_LEVEL`：日志级别（DEBUG / INFO / WARNING / ERROR）
- `DATA_DIR`：数据存储目录（默认 `./data`）
- `MAX_RETRIES`：API 失败重试次数（默认 3）
- `ENABLE_SPEAKER_DIARIZATION`：是否启用说话人识别（默认 true）

---

## 项目结构

```
podcast_notes/
├── assets/               # 项目资源（demo 视频、预览图等）
├── backend/              # FastAPI 后端
│   ├── routers/          # API 路由（搜索/转写/处理/下载/库/...）
│   ├── middleware/       # 鉴权 / 限流 / 校验
│   └── main.py
├── core/                 # 核心处理模块
│   ├── transcriber.py    # 语音转写
│   ├── content_processor.py  # 内容理解与笔记生成
│   ├── image_generator.py    # 图文卡片渲染
│   ├── proofreader.py    # AI 校对
│   └── document_validator.py
├── models/               # 数据模型
├── services/             # 服务层
│   ├── llm_service.py
│   └── podcast_search.py
├── prompts/              # Prompt 模板（v1-v9）
├── templates/            # 图文 HTML 模板
│   ├── minimal/          # 极简知识感
│   ├── vibrant/          # 活力社交感
│   ├── editorial/        # 高级杂志感
│   └── styles/design-tokens.css
├── web-dashboard/        # Next.js 前端
│   └── src/
│       ├── app/dashboard/  # 搜索/创建/库/设置
│       └── components/     # 预览/下载/校对等组件
├── scripts/              # CLI 脚本
├── tests/                # 测试
├── docs/                 # 项目文档
│   ├── PRD.md            # 产品需求文档
│   └── download-feature-guide.md
├── nginx/                # 反代配置
├── prometheus/           # 监控配置
├── docker-compose.yml
├── Dockerfile.backend
└── Dockerfile.frontend
```

---

## 路线图

- [x] **V1.0 MVP**：核心链路打通，9 套模板 + 3 种风格 + Web 后台 + Docker 化部署
- [ ] **V1.1 体验优化**：首次使用引导 / 转录查看器优化 / 笔记阅读器完整化 / 移动端适配
- [ ] **V1.2 内容质量**：模板智能推荐 / 库内全文检索 / 批量处理 / 多 LLM 切换 UI
- [ ] **V2.0 长期演进**：跨期主题聚合 / 个人内容画像 / RAG 检索增强

明确**不做**：自动发布到平台（创作者需要终审权）、多用户 SaaS 化、付费墙。详见 [PRD §8.5](docs/PRD.md#八项目排期与优先级)。

---

## 技术栈

| 层级 | 选型 |
|-----|------|
| 前端 | Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 |
| 后端 | FastAPI + Pydantic v2 + Uvicorn |
| 语音转写 | SenseVoice / faster-whisper / Whisper / ElevenLabs Scribe |
| LLM | OpenAI / Anthropic Claude / DeepSeek / Ollama（本地） |
| 模板渲染 | Jinja2 + Playwright（HTML → PNG） |
| 数据库 | SQLite（默认）→ PostgreSQL（生产） |
| 缓存 | Redis |
| 部署 | Docker + Docker Compose + Nginx |
| 监控 | Prometheus + Grafana |
| 日志 | structlog（结构化 JSON 日志） |
| 测试 | pytest（后端）+ Vitest（前端） |

---

## 相关文档

- 📋 [产品需求文档 PRD](docs/PRD.md) — 完整的产品设计与功能规划
- 🎨 [设计系统规范](DESIGN_SYSTEM.md) — 三层 Token 架构与三种视觉风格
- ⬇️ [下载功能指南](docs/download-feature-guide.md) — 文档导出详细说明
- 🏗️ [部署运维方案](.trae/documents/deployment-optimization-plan.md) — Docker + Nginx + Prometheus 生产部署

---

## 参与贡献

我们欢迎任何形式的贡献：提 Issue、提 PR、写文档、分享使用案例。

请阅读 [贡献指南](.trae/documents/) 了解开发规范和提交流程。

### 本地开发

```bash
# 后端测试
pytest tests/ -v

# 前端 lint + type check
cd web-dashboard
npm run lint
npx tsc --noEmit

# 端到端验证
docker compose -f docker-compose.yml up
```

### 提交规范

遵循 Conventional Commits：

```
feat: 新增批量处理功能
fix: 修复英文转写失败问题
docs: 更新 README 安装说明
refactor: 重构 LLM 服务调用层
test: 补充转写器单元测试
```

---

## 安全与隐私

- **本地优先**：所有数据处理在本地完成，API 密钥不离开你的电脑
- **密钥保护**：`.env` 在 `.gitignore` 中，仓库中不会有任何真实密钥
- **开源可审计**：MIT 协议，代码完全公开
- **无追踪**：不内置任何遥测/分析代码

如果你发现安全漏洞，请**不要**在公开 Issue 中提及，私下联系维护者。

---

## 致谢

本项目使用了许多优秀的开源项目：

- [OpenAI Whisper](https://github.com/openai/whisper) / [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / [FunASR SenseVoice](https://github.com/modelscope/FunASR)
- [FastAPI](https://fastapi.tiangolo.com/) / [Pydantic](https://docs.pydantic.dev/)
- [Next.js](https://nextjs.org/) / [Tailwind CSS](https://tailwindcss.com/) / [Framer Motion](https://www.framer.com/motion/)
- [Playwright](https://playwright.dev/) / [Jinja2](https://jinja.palletsprojects.com/)

---

## 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

---

## English

**Podcast Notes** — Turn the podcasts you listen to into searchable, downloadable, repurposable knowledge assets.

Upload an audio file and get: transcript → structured notes → visual cards ready to publish.

### Key Features

- **9 note templates** (v1-v9): from standard summary to deep causal analysis
- **3 visual styles**: minimal / vibrant / editorial, switchable via design tokens
- **Multi-engine STT**: SenseVoice (Chinese-optimized) / faster-whisper (English) / Whisper
- **Multi-LLM support**: OpenAI / Anthropic / Ollama / DeepSeek
- **Speaker diarization**: distinguish host vs guest vs guest
- **Auto source attribution**: every note is tagged with the source podcast
- **Web dashboard + CLI**: use the GUI or script batch processing
- **Local-first**: all data stays on your machine

### Quick Start

```bash
git clone https://github.com/dession-wu/podcast_notes.git
cd podcast_notes
cp .env.example .env   # fill in your API keys
docker compose up -d
```

Then open:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

For more details, see the [Chinese section above](#播客笔记--podcast-notes) and the full [PRD](docs/PRD.md).

---

<p align="center">
  Made with care for podcast lovers and content creators.
</p>
