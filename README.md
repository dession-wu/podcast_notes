# 播客转小红书自动化工作流

> 从播客音频抓取 → 语音转文字 → AI 内容提炼 → 小红书图文发布的端到端自动化工作流

## 功能特性

- **音频抓取**：支持 RSS 订阅源解析、本地音频文件上传
- **语音转文字**：集成 Whisper / faster-whisper，支持中文优化
- **AI 内容提炼**：自动提取核心论点、金句、数据案例
- **小红书风格化**：3 种文案模板（标准/深度干货/故事共鸣）
- **合规保障**：自动添加来源标注，避免版权风险

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone <repo-url>
cd podcast-to-xhs

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[whisper]"
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入 API 密钥等配置
```

### 3. 运行工作流

```bash
# 从 RSS 订阅源处理最新一期
python scripts/download_and_process.py --rss https://example.com/feed.xml

# 处理本地音频文件
python scripts/download_and_process.py --audio ./podcast_episode.mp3

# 使用深度干货模板
python scripts/download_and_process.py --rss https://example.com/feed.xml --template v2
```

## 项目结构

```
podcast-to-xhs/
├── config/              # 配置管理
├── core/                # 核心处理模块
│   ├── audio_downloader.py   # 音频下载
│   ├── transcriber.py        # 语音转文字
│   └── content_processor.py  # 内容处理
├── models/              # 数据模型
├── prompts/             # Prompt 模板
├── services/            # 服务层
├── scripts/             # 执行脚本
├── tests/               # 测试
└── data/                # 数据存储
```

## 技术栈

- **Python 3.10+**
- **Pydantic** — 数据验证与配置管理
- **Whisper** — 语音转文字
- **Jinja2** — Prompt 模板渲染
- **structlog** — 结构化日志
- **tenacity** — 重试与弹性模式

## 开发路线图

- [x] V1.0 MVP — 半自动副驾模式
- [ ] V2.0 — MCP 架构与 RPA 自动发布
- [ ] V3.0 — 全自动定时矩阵

## 许可证

MIT License
