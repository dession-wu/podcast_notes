FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
# Optional local STT stack is large; do not build it until resource costs are reviewed.
ARG INSTALL_LOCAL_STT=false
RUN if [ "$INSTALL_LOCAL_STT" = "true" ]; then pip install --no-cache-dir faster-whisper funasr torch torchaudio; fi
COPY backend /app/backend
COPY config /app/config
COPY core /app/core
COPY models /app/models
COPY services /app/services
COPY utils /app/utils
RUN useradd -m -u 1000 mini && mkdir /data && chown mini:mini /data
USER mini
ENV MINI_DATA_DIR=/data MINI_DEVELOPMENT=false MINI_DEMO=false
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/mini/health',timeout=3)"
CMD ["python", "-m", "uvicorn", "backend.mini.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8010", "--workers", "1", "--no-proxy-headers"]
