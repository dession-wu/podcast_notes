# Podcast Notes 后端 — FastAPI + Playwright(图片渲染)
# 基础镜像: python:3.10-slim-bookworm (Debian 12)
# 注意: 必须显式指定 bookworm —— 默认 slim tag 是 bullseye(Debian 11),
# 而 Playwright 1.62 已不支持 debian11-x64, 会报 "Cannot install dependencies"
FROM python:3.10-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/

# apt 换源到阿里云镜像（境外 deb.debian.org 在 ECS 上下载停滞）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' \
        /etc/apt/sources.list.d/* /etc/apt/sources.list 2>/dev/null || true

# 系统依赖: curl(健康检查) + Chromium 渲染所需字体(中文截图必需)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖分层: 先装 pip 依赖(含 playwright 包)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# 安装 Chromium 浏览器及其系统依赖(npmmirror 镜像加速)
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# 应用代码
COPY backend /app/backend
COPY config /app/config
COPY core /app/core
COPY models /app/models
COPY services /app/services
COPY utils /app/utils
COPY prompts /app/prompts
COPY templates /app/templates

# 非 root 用户运行
RUN useradd -r -m -u 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

ENV DATA_DIR=/app/data

EXPOSE 8000

# 健康检查: /api/health 在后端鉴权白名单内, 无需 API Key; 用 127.0.0.1 规避 IPv6 解析问题
HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health/ || exit 1

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]