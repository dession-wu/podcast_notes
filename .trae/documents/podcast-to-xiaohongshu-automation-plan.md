# 播客转小红书自动化工作流 — 项目规划文档

> **项目愿景**：构建一个从播客音频抓取 → 语音转文字 → AI 内容提炼 → 小红书图文发布的端到端自动化工作流，打造"AI 内容矩阵"的核心引擎。

---

## 一、可行性评估与优化建议

### 1.1 整体可行性结论

| 维度 | 评估 | 说明 |
|------|------|------|
| 技术可行性 | **高** | 所有技术节点均有成熟开源方案或 API 支持 |
| 成本可控性 | **高** | V1 可完全基于开源本地模型实现零 API 成本 |
| 法律合规性 | **中** | 需严格遵循内容引用规范，避免版权风险 |
| 小红书发布稳定性 | **中** | RPA 方案存在平台策略变动风险，需设计降级策略 |

### 1.2 各节点优化建议

#### Node 1: 音频抓取 — 优化后方案

**原方案问题**：
- `feedparser` 解析 RSS 只能获取公开 RSS 的播客，小宇宙上大量播客没有公开 RSS
- `yt-dlp` 对小宇宙网页版的支持未经充分验证

**优化方案（三层降级策略）**：

```
优先级 1: RSS 订阅源解析（feedparser）
    ↓ 如果 RSS 不可用
优先级 2: 小宇宙网页版抓取（Playwright + 页面解析）
    ↓ 如果网页版受限
优先级 3: 手动音频文件上传（预留接口，用户手动提供 MP3）
```

**技术选型确认**：
- **主选**：`feedparser` + `requests` 下载 MP3
- **备选**：`playwright` 模拟浏览器抓取小宇宙页面
- **兜底**：本地文件上传接口

---

#### Node 2: 语音转文字 — 优化后方案

**原方案问题**：
- SenseVoice 本地部署对 GPU 有要求，纯 CPU 环境转录长音频较慢
- Kimi/通义千问直接上传音频的方案未经成本测算

**优化方案（按场景选择）**：

| 场景 | 推荐方案 | 成本 | 速度 |
|------|----------|------|------|
| 本地有 GPU (CUDA) | SenseVoice (本地) | 免费 | 极快 |
| 本地无 GPU | Whisper.cpp (本地 CPU) | 免费 | 中等 |
| 追求便捷 | ElevenLabs Scribe v2 API | 按量计费 | 极快 |
| 追求性价比 | 通义千问 / Kimi 音频 API | 按量计费 | 快 |

**推荐实现**：
- V1 版本使用 **Whisper.cpp**（纯 CPU 可运行，中文效果足够好）
- 提供配置开关，允许切换到 API 模式（SenseVoice / ElevenLabs / 大模型 API）

---

#### Node 3: 内容提炼与小红书体改写 — 优化后方案

**原方案问题**：
- 单纯依赖 Prompt Engineering 难以保证输出质量的一致性
- 缺少对播客内容结构的深度理解（如嘉宾对话 vs 单人讲述）

**优化方案（结构化 RAG 流程）**：

```
转录文本
    ↓
[文本预处理] → 分段、去口头禅、识别说话人
    ↓
[内容理解] → 提取核心论点、金句、数据、案例
    ↓
[小红书风格化] → 套用模板生成最终文案
    ↓
[质量检查] → 检查字数、标签数量、合规性
```

**Prompt 模板体系**：
- `prompts/xiaohongshu_note_v1.md` — 标准笔记模板
- `prompts/xiaohongshu_note_v2.md` — 深度干货模板
- `prompts/xiaohongshu_note_v3.md` — 故事共鸣模板

**LLM 选型**：
- **本地**：Ollama + Qwen2.5 / DeepSeek（零成本，隐私好）
- **API**：Claude 3.5 Sonnet / GPT-4o / 通义千问（质量高，速度快）

---

#### Node 4: 自动发布到小红书 — 优化后方案

**原方案问题**：
- Playwright/Selenium 模拟发布存在被检测风险
- Cookie 登录态可能过期，维护成本高

**优化方案（分层发布策略）**：

```
优先级 1: RPA 自动化发布（Playwright）
    - 使用已登录的 Chrome Profile
    - 模拟人类操作间隔（随机延迟 1-3 秒）
    - 失败时截图保存用于调试
    ↓ 如果 RPA 失效
优先级 2: 半自动发布助手
    - 自动生成发布文案并复制到剪贴板
    - 自动打开小红书创作中心网页
    - 用户手动粘贴确认发布
    ↓ 如果网页版不可用
优先级 3: 纯手动模式
    - 输出完整的发布文案 + 封面图
    - 用户完全手动操作
```

**关键实现细节**：
- 使用 `baoyu-post-to-weibo` 技能的同款 CDP 技术（Chrome DevTools Protocol）
- 小红书网页版地址：`https://www.xiaohongshu.com/creator/notes`
- 必须实现 **操作间隔随机化** 和 **异常截图保存**

---

## 二、技术架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        播客转小红书工作流                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   输入层      │    │   处理层      │    │   输出层      │      │
│  │              │    │              │    │              │      │
│  │ • RSS URL    │───→│ • 音频下载    │───→│ • 小红书文案  │      │
│  │ • 小宇宙链接  │    │ • 语音转文字  │    │ • 封面图片    │      │
│ │ • 本地 MP3   │    │ • AI 内容提炼 │    │ • 发布状态    │      │
│  │              │    │ • 风格化改写  │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         ↓                   ↓                   ↓               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │                    配置与调度层                        │      │
│  │  • config.yaml (API 密钥、模型选择、发布配置)          │      │
│  │  • task_scheduler.py (定时任务、批量处理)              │      │
│  │  • state_manager.py (任务状态持久化)                   │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块设计

```
podcast-to-xhs/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Pydantic Settings 配置管理
│   └── config.yaml          # 用户配置文件模板
│
├── core/
│   ├── __init__.py
│   ├── audio_downloader.py   # Node 1: 音频抓取
│   ├── transcriber.py        # Node 2: 语音转文字
│   ├── content_processor.py  # Node 3: 内容提炼与改写
│   └── publisher.py          # Node 4: 小红书发布
│
├── models/
│   ├── __init__.py
│   ├── podcast.py            # 播客数据模型
│   ├── transcript.py         # 转录文本模型
│   └── xiaohongshu.py        # 小红书笔记模型
│
├── prompts/
│   ├── xiaohongshu_note_v1.md
│   ├── xiaohongshu_note_v2.md
│   └── xiaohongshu_note_v3.md
│
├── services/
│   ├── __init__.py
│   ├── llm_service.py        # LLM 调用封装
│   ├── stt_service.py        # 语音转文字服务封装
│   └── image_service.py      # 封面图生成服务
│
├── utils/
│   ├── __init__.py
│   ├── logger.py             # 结构化日志
│   ├── retry.py              # 重试装饰器
│   └── validators.py         # 输入验证
│
├── tests/
│   ├── __init__.py
│   ├── test_downloader.py
│   ├── test_transcriber.py
│   └── test_processor.py
│
├── scripts/
│   ├── download_and_process.py   # 单次处理脚本
│   ├── batch_process.py          # 批量处理脚本
│   └── schedule_worker.py        # 定时任务 worker
│
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 三、技术选型详表

### 3.1 依赖库清单

| 类别 | 库名 | 版本 | 用途 |
|------|------|------|------|
| 配置管理 | `pydantic-settings` | ^2.0 | 环境变量与配置验证 |
| 音频下载 | `feedparser` | ^6.0 | RSS 解析 |
| | `requests` | ^2.31 | HTTP 下载 |
| | `yt-dlp` | ^2024.1 | 万能音视频下载 |
| 语音转文字 | `openai-whisper` | ^20231117 | OpenAI Whisper 本地版 |
| | `faster-whisper` | ^1.0 | 更快的 Whisper 实现 |
| | `sensevoice` | latest | 阿里 SenseVoice（可选） |
| LLM 调用 | `openai` | ^1.0 | OpenAI API 客户端 |
| | `anthropic` | ^0.18 | Claude API 客户端 |
| | `ollama` | ^0.1 | 本地 Ollama 调用 |
| 浏览器自动化 | `playwright` | ^1.40 | 小红书网页版 RPA |
| 任务调度 | `apscheduler` | ^3.10 | 定时任务调度 |
| 数据处理 | `pydantic` | ^2.5 | 数据模型验证 |
| | `jinja2` | ^3.1 | Prompt 模板渲染 |
| 日志与监控 | `structlog` | ^24.1 | 结构化日志 |
| 测试 | `pytest` | ^8.0 | 单元测试 |
| | `pytest-asyncio` | ^0.23 | 异步测试支持 |
| | `respx` | ^0.20 | HTTP 请求 Mock |

### 3.2 外部服务/API

| 服务 | 用途 | 成本 | 优先级 |
|------|------|------|--------|
| Ollama (本地) | 本地 LLM 推理 | 免费 | P0 |
| OpenAI API | GPT-4o / Whisper API | 按量 | P1 |
| Anthropic API | Claude 3.5 Sonnet | 按量 | P1 |
| 通义千问 API | 中文场景优化 | 按量 | P2 |
| ElevenLabs Scribe | 高精度语音转文字 | 按量 | P2 |

---

## 四、开发路线图（三期规划）

### V1.0 半自动副驾模式（MVP）— 预计 1-2 周

**目标**：跑通核心数据处理流，验证技术可行性

**功能范围**：
- [ ] 支持 RSS 订阅源解析下载音频
- [ ] 支持本地 MP3 文件上传
- [ ] 集成 Whisper.cpp 本地转录（中文优化）
- [ ] 实现基础小红书风格化 Prompt
- [ ] 输出格式化的小红书文案到终端/文件
- [ ] 手动复制粘贴发布（半自动）

**交付物**：
- `scripts/download_and_process.py` — 单次处理脚本
- `config/config.yaml` — 配置文件模板
- `prompts/xiaohongshu_note_v1.md` — 基础 Prompt 模板

**验收标准**：
- 输入一个播客 RSS 链接，5 分钟内输出可用的小红书文案
- 转录准确率 > 85%（中文场景）
- 文案字数控制在 300-800 字（小红书 optimal）

---

### V2.0 MCP 架构与增强功能 — 预计 2-3 周

**目标**：模块化架构，支持多种输入源和发布方式

**功能范围**：
- [ ] 重构为 MCP Server 架构（可选）
- [ ] 支持小宇宙网页版直接抓取
- [ ] 集成多种 LLM 提供商（OpenAI / Claude / Ollama）
- [ ] 实现多种小红书文案风格模板
- [ ] 自动封面图生成（AI 图片生成）
- [ ] RPA 自动发布到小红书（Playwright）
- [ ] 任务状态持久化（SQLite/JSON）

**交付物**：
- `core/` 模块完整实现
- `services/` 服务层封装
- `scripts/batch_process.py` — 批量处理
- `scripts/schedule_worker.py` — 定时任务

**验收标准**：
- 支持至少 3 种不同风格的文案生成
- RPA 发布成功率 > 80%
- 批量处理 10 期播客无中断

---

### V3.0 全自动矩阵模式 — 预计 3-4 周

**目标**：无人值守的自动化内容矩阵

**功能范围**：
- [ ] 云端部署支持（Docker / VPS）
- [ ] GitHub Actions / Cron 定时调度
- [ ] 多账号管理与轮换
- [ ] 内容去重与查重机制
- [ ] 发布数据分析与反馈闭环
- [ ] Web UI 管理面板（可选）

**交付物**：
- `Dockerfile` + `docker-compose.yml`
- `.github/workflows/schedule.yml`
- `web/` 管理面板（可选）

**验收标准**：
- 每日自动抓取并处理订阅的播客更新
- 多账号发布无冲突
- 系统连续运行 7 天无故障

---

## 五、关键风险与应对策略

### 5.1 技术风险

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| 小红书网页版改版导致 RPA 失效 | 中 | 高 | 设计半自动降级模式；定期更新选择器 |
| 本地 Whisper 转录速度慢 | 中 | 中 | 提供 API 模式切换；支持 GPU 加速 |
| LLM API 成本超预期 | 低 | 中 | 默认使用本地 Ollama；API 模式可配置 |
| 播客 RSS 失效或反爬 | 中 | 中 | 多层降级策略；支持手动上传 |

### 5.2 法律合规风险

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| 内容侵权投诉 | 中 | 高 | 强制标注来源；仅做内容提炼不搬运全文 |
| 小红书账号封禁 | 中 | 高 | 控制发布频率（每日 1-2 条）；多账号轮换 |
| 违反平台用户协议 | 中 | 中 | 使用 RPA 而非破解 API；模拟人类操作 |

### 5.3 缓解措施清单

- [ ] 所有生成内容必须包含 `"🎙️ 本文灵感/内容提炼自播客《XXX》第 X 期"`
- [ ] 每日发布频率限制为 1-2 条
- [ ] 实现内容指纹去重，避免重复发布相似内容
- [ ] 定期备份账号 Cookie 和登录态
- [ ] 监控 RPA 操作成功率，失败时自动切换降级模式

---

## 六、Prompt 工程规范

### 6.1 小红书文案生成 Prompt 模板结构

```markdown
# Role
你是一位资深的小红书内容运营专家，擅长将长音频内容提炼成高互动率的图文笔记。

# Input
播客标题：{{ podcast_title }}
播客嘉宾：{{ guests }}
转录文本：{{ transcript }}

# Task
1. 提取 1 个最具反常识/共鸣感的金句作为标题（20 字以内）
2. 提炼 3-5 个核心干货要点，每个要点配一个 emoji
3. 生成 3-5 个相关话题标签
4. 在开头标注内容来源

# Output Format
```
🎙️ 本文灵感/内容提炼自播客《{{ podcast_title }}》

{{ hook_title }}

💡 核心要点：
• {{ point_1 }}
• {{ point_2 }}
• {{ point_3 }}

🔖 {{ tag_1 }} {{ tag_2 }} {{ tag_3 }}
```

# Constraints
- 总字数控制在 300-800 字
- 使用口语化表达，避免学术腔
- 每个要点必须包含具体 actionable 建议
```

### 6.2 封面图生成 Prompt 模板

```markdown
为播客《{{ podcast_title }}》生成一张小红书封面图：
- 风格：简洁现代，信息层次清晰
- 配色：暖色调，高对比度
- 元素：播客主题相关的视觉符号
- 文字：主标题 "{{ hook_title }}" 醒目展示
- 比例：3:4（小红书竖图标准）
```

---

## 七、开发环境配置

### 7.1 最小硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 存储 | 10 GB | 50 GB+ |
| GPU | 无（CPU 模式） | NVIDIA CUDA 兼容 |

### 7.2 环境初始化步骤

```bash
# 1. 克隆仓库
git clone <repo-url>
cd podcast-to-xhs

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 Whisper 模型（首次运行）
whisper --model medium --download-only

# 5. 安装 Playwright 浏览器
playwright install chromium

# 6. 复制并编辑配置文件
cp .env.example .env
# 编辑 .env 填入 API 密钥等配置

# 7. 运行测试
pytest tests/ -v
```

### 7.3 配置文件模板 (.env.example)

```bash
# LLM 配置
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://localhost:11434
DEFAULT_LLM_PROVIDER=ollama  # openai / anthropic / ollama

# 语音转文字配置
STT_PROVIDER=whisper  # whisper / sensevoice / elevenlabs
ELEVENLABS_API_KEY=...

# 小红书发布配置
XIAOHONGSHU_RPA_ENABLED=true
XIAOHONGSHU_CHROME_PROFILE=/path/to/chrome/profile
XIAOHONGSHU_PUBLISH_MODE=rpa  # rpa / semi-auto / manual

# 系统配置
LOG_LEVEL=INFO
DATA_DIR=./data
```

---

## 八、测试策略

### 8.1 测试金字塔

```
        /\
       /  \      E2E 测试 (RPA 发布流程)
      /____\        
     /      \    集成测试 (音频→转录→文案)
    /________\      
   /          \  单元测试 (各模块独立测试)
  /____________\
```

### 8.2 关键测试用例

| 模块 | 测试用例 | 类型 |
|------|----------|------|
| AudioDownloader | test_download_from_rss_success | 单元 |
| | test_download_from_rss_invalid_url | 单元 |
| | test_download_timeout_retry | 单元 |
| Transcriber | test_transcribe_local_file | 单元 |
| | test_transcribe_empty_audio | 单元 |
| ContentProcessor | test_generate_xiaohongshu_note | 单元 |
| | test_note_word_count_constraint | 单元 |
| | test_source_attribution_required | 单元 |
| Publisher | test_rpa_publish_success | 集成 |
| | test_rpa_publish_login_expired | 集成 |
| EndToEnd | test_full_workflow_rss_to_note | E2E |

---

## 九、部署与运维

### 9.1 Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright
RUN playwright install chromium

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

CMD ["python", "scripts/schedule_worker.py"]
```

### 9.2 GitHub Actions 定时任务

```yaml
# .github/workflows/daily-publish.yml
name: Daily Podcast to Xiaohongshu

on:
  schedule:
    - cron: '0 8 * * *'  # 每天上午 8 点
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
      
      - name: Run workflow
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          XIAOHONGSHU_COOKIE: ${{ secrets.XIAOHONGSHU_COOKIE }}
        run: python scripts/batch_process.py --config config/production.yaml
```

---

## 十、附录

### A. 参考资源

- [Whisper 官方文档](https://github.com/openai/whisper)
- [SenseVoice 开源仓库](https://github.com/FunAudioLLM/SenseVoice)
- [Playwright 文档](https://playwright.dev/python/)
- [小红书创作者中心](https://www.xiaohongshu.com/creator/notes)
- [MCP 协议规范](https://modelcontextprotocol.io/)

### B. 术语表

| 术语 | 说明 |
|------|------|
| RSS | Really Simple Syndication，播客订阅源格式 |
| STT | Speech-to-Text，语音转文字 |
| RPA | Robotic Process Automation，机器人流程自动化 |
| MCP | Model Context Protocol，模型上下文协议 |
| CDP | Chrome DevTools Protocol，浏览器调试协议 |

### C. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v0.1 | 2026-05-19 | 初始规划文档 |

---

> **下一步行动**：确认本规划后，立即开始 V1.0 MVP 开发，优先实现 `audio_downloader` + `transcriber` + `content_processor` 核心链路。
