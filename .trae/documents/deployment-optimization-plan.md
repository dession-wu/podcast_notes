# 播客笔记项目生产部署优化方案

**文档版本**：V1.0  
**撰写日期**：2026-05-30  
**文档状态**：待评审

---

## 一、当前部署架构分析

### 1.1 项目技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| 前端框架 | Next.js 16.2.6 + React 19 | App Router 模式，客户端组件为主 |
| 样式系统 | Tailwind CSS 4 + CSS Custom Properties | 三层 Token 设计系统 |
| 后端 API | FastAPI (Python) | 异步 API，Pydantic 数据验证 |
| 语音转写 | Whisper / faster-whisper / SenseVoice | 本地模型推理 |
| LLM 服务 | OpenAI / Anthropic / Ollama | 多提供商支持 |
| 数据存储 | 本地文件系统 (JSON + Markdown) | 无数据库依赖 |
| 配置管理 | Pydantic Settings + .env | 环境变量驱动 |

### 1.2 当前构建模式

#### 前端构建

```json
// web-dashboard/package.json
{
  "scripts": {
    "dev": "next dev",      // 开发模式
    "build": "next build",  // 生产构建
    "start": "next start"   // 生产启动
  }
}
```

**当前配置问题**：
- `next.config.ts` 仅配置了 API 代理 rewrite，缺少生产优化配置
- 无静态导出配置（`output: 'export'`）
- 无图片优化配置（`images.unoptimized`）
- 无代码分割和缓存策略配置

#### 后端构建

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

**当前配置问题**：
- 无 Docker 容器化配置
- 无生产级 WSGI/ASGI 服务器（如 Uvicorn + Gunicorn）
- 无进程管理工具（如 Supervisor/Systemd）
- 无日志轮转和监控

### 1.3 部署架构现状

```
当前部署模式（开发模式）
├── 前端: Next.js dev server (port 3000)
│   └── 通过 rewrites 代理 API 请求到后端
├── 后端: Python 直接运行 (port 8000)
│   └── 无进程守护，崩溃后无法自动恢复
└── 数据: 本地文件系统
    └── 无备份策略，数据丢失风险
```

---

## 二、生产环境风险评估

### 2.1 高风险项

| 风险编号 | 风险描述 | 影响 | 优先级 |
|---------|---------|------|-------|
| R1 | **无容器化部署** | 环境不一致，部署困难 | 🔴 P0 |
| R2 | **Next.js dev server 用于生产** | 性能差，无优化，安全风险 | 🔴 P0 |
| R3 | **Python 直接运行，无进程管理** | 崩溃后无法自动恢复 | 🔴 P0 |
| R4 | **API 密钥硬编码在 .env** | 泄露风险，无法轮换 | 🔴 P0 |
| R5 | **无 HTTPS/TLS** | 数据传输不安全 | 🔴 P0 |

### 2.2 中风险项

| 风险编号 | 风险描述 | 影响 | 优先级 |
|---------|---------|------|-------|
| R6 | **无静态资源 CDN** | 加载速度慢 | 🟠 P1 |
| R7 | **无日志收集和监控** | 问题排查困难 | 🟠 P1 |
| R8 | **无数据备份策略** | 数据丢失风险 | 🟠 P1 |
| R9 | **无负载均衡** | 单点故障，无法扩展 | 🟠 P1 |
| R10 | **大模型文件未优化** | Whisper 模型体积大，启动慢 | 🟠 P1 |

### 2.3 低风险项

| 风险编号 | 风险描述 | 影响 | 优先级 |
|---------|---------|------|-------|
| R11 | **无 CI/CD 流水线** | 部署效率低 | 🟡 P2 |
| R12 | **无自动化测试** | 回归风险 | 🟡 P2 |
| R13 | **前端无 PWA 支持** | 离线体验差 | 🟡 P2 |

---

## 三、生产级部署优化方案

### 3.1 总体架构设计

```
生产部署架构
├── 负载均衡层 (Nginx / Traefik)
│   ├── HTTPS 终止
│   ├── 静态资源缓存
│   └── 反向代理到服务
├── 前端服务 (Next.js 静态导出 + Nginx)
│   ├── 静态 HTML/CSS/JS
│   └── 图片和字体 CDN
├── 后端服务 (FastAPI + Uvicorn)
│   ├── 多工作进程 (Gunicorn)
│   ├── 自动重启 (Supervisor)
│   └── 健康检查端点
├── 数据层
│   ├── 持久化卷 (Docker Volume)
│   └── 定时备份 (Cron + Rsync)
└── 监控层
    ├── 日志收集 (Loki / Fluentd)
    ├── 指标监控 (Prometheus + Grafana)
    └── 告警通知 (Alertmanager)
```

### 3.2 优化实施步骤

#### 阶段一：容器化改造（P0）

##### Step 1: 创建 Dockerfile（前端）

```dockerfile
# web-dashboard/Dockerfile
# 多阶段构建，减小镜像体积

# 阶段一：依赖安装
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# 阶段二：构建
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build

# 阶段三：运行
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 创建非 root 用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制构建产物
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

##### Step 2: 更新 next.config.ts（生产配置）

```typescript
import type { NextConfig } from "next";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // 输出 standalone 模式，用于 Docker 部署
  output: "standalone",

  // 图片优化配置
  images: {
    unoptimized: true, // 如果使用静态导出或 Docker 部署
  },

  // 压缩配置
  compress: true,

  // 实验性功能
  experimental: {
    // 优化包体积
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },

  // API 代理
  async rewrites() {
    return [
      {
        source: "/api/:path*/",
        destination: `${API_BASE_URL}/api/:path*/`,
      },
      {
        source: "/api/:path*",
        destination: `${API_BASE_URL}/api/:path*`,
      },
    ];
  },

  // 安全头
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
```

##### Step 3: 创建 Dockerfile（后端）

```dockerfile
# Dockerfile (项目根目录)
# Python 后端服务

FROM python:3.11-slim AS builder

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[whisper,playwright]"

# 生产镜像
FROM python:3.11-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 复制依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 使用 Uvicorn 运行
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

##### Step 4: 创建 docker-compose.yml

```yaml
version: "3.8"

services:
  # 前端服务
  frontend:
    build:
      context: ./web-dashboard
      dockerfile: Dockerfile
    container_name: podcast-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - podcast-network

  # 后端服务
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: podcast-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - DATA_DIR=/app/data
    volumes:
      - podcast-data:/app/data
      - ./.env:/app/.env:ro
    networks:
      - podcast-network
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: podcast-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - podcast-data:/app/data:ro
    depends_on:
      - frontend
      - backend
    networks:
      - podcast-network

volumes:
  podcast-data:
    driver: local

networks:
  podcast-network:
    driver: bridge
```

##### Step 5: 创建 Nginx 配置

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # 前端服务
    server {
        listen 80;
        server_name _;

        # 静态资源缓存
        location /_next/static/ {
            proxy_pass http://frontend:3000;
            proxy_cache_valid 200 365d;
            add_header Cache-Control "public, immutable";
        }

        # 前端页面
        location / {
            proxy_pass http://frontend:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # API 代理
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
    }
}
```

#### 阶段二：安全配置（P0）

##### Step 1: 环境变量管理

创建 `.env.example` 模板：

```bash
# 应用配置
LOG_LEVEL=INFO
DATA_DIR=/app/data

# LLM 配置
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
OLLAMA_HOST=http://localhost:11434

# STT 配置
STT_PROVIDER=faster-whisper
WHISPER_MODEL=medium

# 说话人分离
ENABLE_SPEAKER_DIARIZATION=false
HF_TOKEN=your_huggingface_token

# 小红书发布
XIAOHONGSHU_PUBLISH_MODE=manual

# 播客搜索
PODCASTINDEX_API_KEY=your_key
PODCASTINDEX_API_SECRET=your_secret
```

##### Step 2: 添加健康检查端点

```python
# backend/routers/health.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str
    version: str

@router.get("", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="1.0.0")
```

#### 阶段三：监控与日志（P1）

##### Step 1: 结构化日志配置

```python
# utils/logger.py 增强
import structlog
import logging
import sys

# 配置标准库日志
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# 配置 structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

##### Step 2: 添加 Prometheus 指标

```python
# backend/middleware/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Request, Response
import time

# 请求计数器
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# 请求延迟
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    http_request_duration.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response
```

#### 阶段四：数据持久化与备份（P1）

##### Step 1: 数据卷配置

```yaml
# docker-compose.prod.yml
volumes:
  podcast-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/podcast-notes/data
```

##### Step 2: 备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/backups/podcast-notes"
DATA_DIR="/opt/podcast-notes/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$DATA_DIR" .

# 保留最近 7 天的备份
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: backup_$TIMESTAMP.tar.gz"
```

#### 阶段五：CI/CD 流水线（P2）

##### Step 1: GitHub Actions 工作流

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push
        run: |
          docker build -t podcast-notes:latest .
          docker push podcast-notes:latest

      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/podcast-notes
            docker-compose pull
            docker-compose up -d
```

---

## 四、部署优化清单

### 4.1 必须完成（P0）

| 任务 | 文件 | 说明 |
|-----|------|------|
| 创建前端 Dockerfile | `web-dashboard/Dockerfile` | 多阶段构建，减小镜像体积 |
| 创建后端 Dockerfile | `Dockerfile` | Python  slim 镜像，非 root 用户 |
| 更新 next.config.ts | `web-dashboard/next.config.ts` | 添加 `output: "standalone"` |
| 创建 docker-compose.yml | `docker-compose.yml` | 编排前端、后端、Nginx |
| 创建 Nginx 配置 | `nginx/nginx.conf` | 反向代理、静态缓存、Gzip |
| 添加健康检查端点 | `backend/routers/health.py` | 容器健康检查 |
| 配置环境变量模板 | `.env.example` | 生产环境配置模板 |

### 4.2 建议完成（P1）

| 任务 | 文件 | 说明 |
|-----|------|------|
| 配置 HTTPS | `nginx/ssl/` | SSL 证书配置 |
| 添加监控指标 | `backend/middleware/metrics.py` | Prometheus 指标暴露 |
| 配置日志收集 | `utils/logger.py` | JSON 结构化日志 |
| 创建备份脚本 | `scripts/backup.sh` | 定时数据备份 |
| 配置资源限制 | `docker-compose.yml` | 内存和 CPU 限制 |

### 4.3 可选完成（P2）

| 任务 | 文件 | 说明 |
|-----|------|------|
| CI/CD 流水线 | `.github/workflows/` | GitHub Actions 自动部署 |
| 自动化测试 | `tests/` | 集成测试和 E2E 测试 |
| PWA 支持 | `web-dashboard/public/manifest.json` | 离线访问支持 |

---

## 五、部署命令

### 5.1 首次部署

```bash
# 1. 克隆代码
git clone <repo-url> /opt/podcast-notes
cd /opt/podcast-notes

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置

# 3. 启动服务
docker-compose up -d --build

# 4. 查看状态
docker-compose ps
docker-compose logs -f
```

### 5.2 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```

### 5.3 监控命令

```bash
# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看资源使用
docker stats

# 健康检查
curl http://localhost/api/health
```

---

## 六、性能优化建议

### 6.1 前端优化

| 优化项 | 当前状态 | 建议 |
|-------|---------|------|
| 图片优化 | 未配置 | 启用 Next.js Image 组件或 CDN |
| 代码分割 | 默认 | 配置动态导入减少首屏加载 |
| 静态导出 | 未配置 | 使用 `output: 'export'` 纯静态部署 |
| 缓存策略 | 无 | 配置 Nginx 静态资源缓存 |

### 6.2 后端优化

| 优化项 | 当前状态 | 建议 |
|-------|---------|------|
| 工作进程 | 单进程 | 使用 Gunicorn + Uvicorn Workers |
| 模型加载 | 每次请求 | 预加载模型到内存 |
| 数据库 | 文件系统 | 考虑 SQLite 或 PostgreSQL |
| 缓存 | 无 | 添加 Redis 缓存层 |

---

## 七、总结

当前项目的构建模式**不适合直接部署到生产环境**。主要问题包括：

1. **无容器化**：环境依赖难以管理，部署复杂
2. **开发服务器用于生产**：Next.js dev server 性能差，无优化
3. **无进程管理**：Python 服务崩溃后无法自动恢复
4. **无安全加固**：缺少 HTTPS、安全头、密钥管理
5. **无监控告警**：问题排查困难，无法及时发现故障

**推荐的部署路径**：

1. **短期（1-2 天）**：完成 Docker 容器化 + docker-compose 编排
2. **中期（1 周）**：添加 Nginx 反向代理 + HTTPS + 监控
3. **长期（1 月）**：CI/CD 流水线 + 自动化测试 + 高可用架构

按此方案实施后，项目可达到生产级部署标准，具备稳定性、安全性和可维护性。
