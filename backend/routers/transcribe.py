"""Transcription router."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from config import settings
from core.smart_transcriber import SmartTranscriber, SmartTranscriberError
from core.transcriber import Transcriber, TranscriberError
from models.podcast import PodcastEpisode
from utils import get_logger
from utils.metrics import metrics_collector

logger = get_logger(__name__)
router = APIRouter()

# Thread pool for running sync transcription in background
transcribe_executor = ThreadPoolExecutor(max_workers=2)

# In-memory job storage (replace with Redis/DB in production)
jobs: dict[str, dict] = {}

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = {".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac", ".wma", ".opus"}
MAX_FILE_SIZE_MB = 500


class TranscriptionErrorCategory:
    """Transcription error categories."""

    FILE_NOT_FOUND = "file_not_found"
    INVALID_FORMAT = "invalid_format"
    FILE_TOO_LARGE = "file_too_large"
    MODEL_LOAD_ERROR = "model_load_error"
    MODEL_NOT_INSTALLED = "model_not_installed"
    TRANSCRIPTION_ERROR = "transcription_error"
    TIMEOUT = "timeout"
    OUT_OF_MEMORY = "out_of_memory"
    UNKNOWN_ERROR = "unknown_error"


def _categorize_error(error: Exception) -> tuple[str, str]:
    """Categorize transcription error and return (category, message)."""
    error_msg = str(error).lower()
    error_type = type(error).__name__

    # File-related errors
    if "not found" in error_msg or "不存在" in error_msg or "no such file" in error_msg:
        return TranscriptionErrorCategory.FILE_NOT_FOUND, "音频文件不存在或已被删除"

    if "format" in error_msg or "not supported" in error_msg or "invalid" in error_msg:
        return TranscriptionErrorCategory.INVALID_FORMAT, "不支持的音频格式"

    if "too large" in error_msg or "size" in error_msg:
        return TranscriptionErrorCategory.FILE_TOO_LARGE, "文件过大，请上传更小的音频文件"

    # Model-related errors
    if "not installed" in error_msg or "未安装" in error_msg or "no module named" in error_msg:
        return (
            TranscriptionErrorCategory.MODEL_NOT_INSTALLED,
            "转录模型未安装，请联系管理员配置",
        )

    if "out of memory" in error_msg or "cuda out of memory" in error_msg or "oom" in error_msg:
        return (
            TranscriptionErrorCategory.OUT_OF_MEMORY,
            "内存不足，无法完成转录",
        )

    if "timeout" in error_msg or "timed out" in error_msg:
        return TranscriptionErrorCategory.TIMEOUT, "转录超时，建议分段处理"

    if "model" in error_msg and ("load" in error_msg or "init" in error_msg or "download" in error_msg):
        return TranscriptionErrorCategory.MODEL_LOAD_ERROR, "转录模型加载失败，请检查模型配置"

    # Specific exception types
    if "modulenotfound" in error_type.lower() or "importerror" in error_type.lower():
        return (
            TranscriptionErrorCategory.MODEL_NOT_INSTALLED,
            f"缺少依赖模块: {str(error)[:100]}",
        )

    if "runtimeerror" in error_type.lower() and ("cuda" in error_msg or "gpu" in error_msg):
        return (
            TranscriptionErrorCategory.MODEL_LOAD_ERROR,
            "GPU/CUDA 错误，尝试使用 CPU 模式",
        )

    if "connection" in error_msg or "network" in error_msg or "urllib" in error_msg:
        return (
            TranscriptionErrorCategory.MODEL_LOAD_ERROR,
            "网络错误，无法下载模型文件",
        )

    # Transcription-specific errors
    if "transcribe" in error_msg or "转录" in error_msg:
        return TranscriptionErrorCategory.TRANSCRIPTION_ERROR, "转录过程中发生错误"

    if "audio" in error_msg or "decode" in error_msg or "ffmpeg" in error_msg:
        return (
            TranscriptionErrorCategory.INVALID_FORMAT,
            "音频解码失败，文件可能已损坏",
        )

    # Default: include error type for better debugging
    return TranscriptionErrorCategory.UNKNOWN_ERROR, f"转录失败 ({error_type}): {str(error)[:200]}"


def get_audio_duration(file_path: Path) -> float | None:
    """获取音频文件时长（秒）.

    优先使用 ffprobe，如果不可用则根据文件大小估算。

    Args:
        file_path: 音频文件路径

    Returns:
        音频时长（秒），如果无法获取则返回 None
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        if duration > 0:
            return duration
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, ValueError):
        pass

    BITRATE_ESTIMATES = {
        ".mp3": 128,
        ".m4a": 128,
        ".aac": 128,
        ".ogg": 128,
        ".wav": 1411,
        ".flac": 800,
    }

    try:
        file_size_bits = file_path.stat().st_size * 8
        ext = file_path.suffix.lower()
        bitrate = BITRATE_ESTIMATES.get(ext, 128) * 1000
        estimated_duration = file_size_bits / bitrate
        if estimated_duration > 0:
            return estimated_duration
    except OSError:
        pass

    return None


def get_hardware_info() -> dict:
    """获取硬件能力信息.

    Returns:
        硬件信息字典
    """
    info = {
        "has_cuda": False,
        "cuda_device": None,
        "cpu_count": os.cpu_count() or 1,
    }
    try:
        import torch
        info["has_cuda"] = torch.cuda.is_available()
        if info["has_cuda"]:
            info["cuda_device"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return info


def calculate_estimate_time(duration_seconds: float, provider: str = "sensevoice") -> dict:
    """计算转录预估时间（基于硬件感知）.

    根据检测到的硬件（CPU/GPU）和选择的引擎，提供更准确的时间预估。

    Args:
        duration_seconds: 音频时长（秒）
        provider: STT 引擎提供商

    Returns:
        预估信息字典
    """
    hardware = get_hardware_info()

    # 基础速度因子（相对于实时）
    # 数值越小越快：<1 表示快于实时，>1 表示慢于实时
    SPEED_FACTORS = {
        "sensevoice": {
            "cuda": 0.3,      # GPU: 3.3x 实时
            "cpu": 3.0,       # CPU: 0.33x 实时
        },
        "whisper": {
            "cuda": 0.5,
            "cpu": 5.0,
        },
        "faster_whisper": {
            "cuda": 0.15,     # GPU: 6.7x 实时
            "cpu": 1.5,       # CPU: 0.67x 实时
        },
        "elevenlabs": {
            "cuda": 0.3,
            "cpu": 0.3,       # API 调用，与硬件无关
        },
    }

    # 确定设备类型
    device = "cuda" if hardware["has_cuda"] else "cpu"

    # 获取速度因子
    provider_speeds = SPEED_FACTORS.get(provider, SPEED_FACTORS["sensevoice"])
    factor = provider_speeds.get(device, provider_speeds["cpu"])

    # 根据 CPU 核心数调整（多核略有优势）
    if device == "cpu" and hardware["cpu_count"]:
        if hardware["cpu_count"] >= 8:
            factor *= 0.9  # 多核优化 10%
        elif hardware["cpu_count"] <= 2:
            factor *= 1.2  # 少核惩罚 20%

    # 计算处理时间
    processing_time = duration_seconds * factor

    # 根据引擎和设备添加开销
    overhead = {
        "sensevoice": 30 if device == "cpu" else 10,
        "whisper": 60 if device == "cpu" else 15,
        "faster_whisper": 20 if device == "cpu" else 5,
        "elevenlabs": 5,
    }.get(provider, 30)

    total_seconds = int(processing_time + overhead)

    # 格式化时间
    if total_seconds < 60:
        formatted = f"{total_seconds}秒"
    elif total_seconds < 3600:
        mins = total_seconds // 60
        secs = total_seconds % 60
        formatted = f"{mins}分{secs}秒" if secs > 0 else f"{mins}分钟"
    else:
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        formatted = f"{hours}小时{mins}分" if mins > 0 else f"{hours}小时"

    # 格式化音频时长
    audio_mins = int(duration_seconds // 60)
    audio_secs = int(duration_seconds % 60)
    if audio_mins >= 60:
        audio_hours = audio_mins // 60
        audio_duration_formatted = f"{audio_hours}:{audio_mins % 60:02d}:{audio_secs:02d}"
    else:
        audio_duration_formatted = f"{audio_mins}:{audio_secs:02d}"

    return {
        "total_seconds": total_seconds,
        "formatted_time": formatted,
        "provider": provider,
        "device": device,
        "audio_duration_seconds": duration_seconds,
        "audio_duration_formatted": audio_duration_formatted,
        "speed_factor": factor,
        "has_cuda": hardware["has_cuda"],
    }


class TranscribeResponse(BaseModel):
    """Transcribe response model."""

    task_id: str
    status: str
    estimate: dict | None = None


class TranscribeStatusResponse(BaseModel):
    """Transcription status response model."""

    task_id: str
    status: str
    progress: float | None = None
    stage: str | None = None
    result: dict | None = None
    error: str | None = None
    error_category: str | None = None
    error_detail: str | None = None
    estimate: dict | None = None
    elapsed_seconds: float | None = None
    remaining_seconds: float | None = None


class TranscribeByPathRequest(BaseModel):
    """Request to transcribe an existing file by path."""

    file_path: str
    force_engine: str | None = None  # "whisper" or "sensevoice", None for auto


def _validate_audio_file(file_path: Path) -> tuple[bool, str]:
    """Validate audio file for transcription.

    Returns:
        (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "文件不存在"

    if file_path.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
        formats = ", ".join(SUPPORTED_AUDIO_FORMATS)
        return False, f"不支持的音频格式，支持: {formats}"

    try:
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return False, f"文件过大 ({size_mb:.1f} MB)，最大支持 {MAX_FILE_SIZE_MB} MB"
    except OSError:
        return False, "无法读取文件信息"

    return True, ""


def _do_transcription(task_id: str, file_path: Path, title: str, force_engine: str | None = None):
    """Run transcription in background thread with smart routing."""
    # Get audio duration for metrics and progress
    duration = get_audio_duration(file_path)

    # Determine provider for metrics
    provider = "sensevoice"  # default
    device = "cpu"

    # Get device info
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"

    # Start metrics collection
    metrics_collector.start_job(
        task_id=task_id,
        audio_duration=duration,
        provider=provider,
        device=device,
    )

    try:
        jobs[task_id]["status"] = "processing"
        jobs[task_id]["progress"] = 5.0

        # Create episode object
        episode = PodcastEpisode(
            title=title,
            audio_url="",
            local_audio_path=file_path,
        )

        jobs[task_id]["progress"] = 10.0

        # Start progress updater thread - ALWAYS start, even without duration
        stop_progress = threading.Event()
        progress_lock = threading.Lock()

        def update_progress():
            """Update progress based on elapsed time vs estimate."""
            start_time = time.time()
            check_interval = 5  # seconds
            stage_names = ["准备中...", "加载模型...", "音频分析...", "语音识别...", "文本整理..."]
            stage_idx = 0
            stage_display_time = 30  # seconds per stage
            
            while not stop_progress.is_set():
                elapsed = time.time() - start_time
                
                with progress_lock:
                    if jobs[task_id]["status"] != "processing":
                        break
                    
                    # Calculate progress
                    if duration and jobs[task_id].get("estimate"):
                        total_estimate = jobs[task_id]["estimate"]["total_seconds"]
                        if total_estimate > 0:
                            # Progress from 10% to 90% based on time
                            time_progress = min(80, (elapsed / total_estimate) * 80)
                            jobs[task_id]["progress"] = round(10 + time_progress, 1)
                        else:
                            # Fallback: increment slowly
                            jobs[task_id]["progress"] = min(85, 10 + (elapsed / 60) * 5)
                    else:
                        # No duration estimate: use stage-based progress
                        stage_idx = min(len(stage_names) - 1, int(elapsed / stage_display_time))
                        stage_progress = (elapsed % stage_display_time) / stage_display_time
                        base_progress = 10 + (stage_idx * 15)
                        jobs[task_id]["progress"] = min(85, base_progress + stage_progress * 15)
                        # Store current stage name
                        jobs[task_id]["stage"] = stage_names[stage_idx]
                
                time.sleep(check_interval)

        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()

        try:
            # Run transcription with smart routing
            transcriber = SmartTranscriber()
            transcript = transcriber.transcribe(episode, force_engine=force_engine)

            # Get language detection info from stt_provider
            engine_used = transcript.stt_provider if transcript.stt_provider else "unknown"
            detection_info = {"language": transcript.language, "method": "auto"}

            jobs[task_id]["status"] = "completed"
            jobs[task_id]["progress"] = 100.0
            jobs[task_id]["result"] = {
                "text": transcript.text,
                "word_count": transcript.word_count,
                "segment_count": transcript.segment_count,
                "language": transcript.language,
                "duration_seconds": transcript.duration_seconds,
                "engine_used": engine_used,
                "language_detected": detection_info.get("language"),
                "detection_method": detection_info.get("method"),
            }

            # Record success metrics
            metrics_collector.end_job(
                task_id=task_id,
                status="completed",
                word_count=transcript.word_count,
            )

            logger.info(
                "Transcription completed",
                task_id=task_id,
                engine=engine_used,
                language=detection_info.get("language"),
                word_count=transcript.word_count,
            )

        finally:
            stop_progress.set()
            progress_thread.join(timeout=2)

    except Exception as e:
        # Capture full error details
        import traceback
        error_traceback = traceback.format_exc()
        category, message = _categorize_error(e)
        
        # Log detailed error for debugging
        logger.error(
            "Transcription failed",
            error=message,
            category=category,
            task_id=task_id,
            traceback=error_traceback,
            original_error=str(e),
        )
        
        jobs[task_id]["status"] = "failed"
        jobs[task_id]["error"] = message
        jobs[task_id]["error_category"] = category
        jobs[task_id]["error_detail"] = str(e)  # Store original error detail
        jobs[task_id]["progress"] = 0  # Reset progress on failure

        # Record failure metrics
        metrics_collector.end_job(
            task_id=task_id,
            status="failed",
            error_category=category,
        )


@router.post("/", response_model=TranscribeResponse)
async def start_transcription(audio: UploadFile = File(...)):
    """Start audio transcription via file upload.

    Args:
        audio: Audio file to transcribe

    Returns:
        Transcribe response with task_id
    """
    task_id = str(uuid.uuid4())

    try:
        # Save uploaded file
        temp_dir = settings.output_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        file_path = temp_dir / f"{task_id}_{audio.filename}"
        with open(file_path, "wb") as f:
            content = await audio.read()
            f.write(content)

        # Validate file
        is_valid, error_msg = _validate_audio_file(file_path)
        if not is_valid:
            # Clean up invalid file
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail=error_msg)

        # 检测音频时长并计算预估时间
        duration = get_audio_duration(file_path)
        estimate = None
        if duration:
            provider = settings.stt_provider.value if hasattr(settings.stt_provider, 'value') else str(settings.stt_provider)
            estimate = calculate_estimate_time(duration, provider)
            logger.info(
                "音频时长检测完成",
                duration_seconds=duration,
                estimate_seconds=estimate["total_seconds"],
                provider=provider,
            )

        # Create job
        jobs[task_id] = {
            "status": "pending",
            "progress": 0.0,
            "file_path": str(file_path),
            "result": None,
            "error": None,
            "error_category": None,
            "estimate": estimate,
            "start_time": time.time(),
        }

        # Start transcription in background
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            transcribe_executor,
            _do_transcription,
            task_id,
            file_path,
            audio.filename or "Uploaded Audio",
            None,  # force_engine: auto-detect
        )

        return TranscribeResponse(task_id=task_id, status="processing", estimate=estimate)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/by-path", response_model=TranscribeResponse)
async def start_transcription_by_path(request: TranscribeByPathRequest):
    """Start transcription for an existing file by path.

    This allows transcribing files already on the server (e.g., downloaded podcasts).
    Supports auto language detection and manual engine override.

    Args:
        request: Contains file_path to the existing audio file, optional force_engine

    Returns:
        Transcribe response with task_id
    """
    task_id = str(uuid.uuid4())
    file_path = Path(request.file_path)

    # Validate file
    is_valid, error_msg = _validate_audio_file(file_path)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 检测音频时长并计算预估时间 (使用智能预估)
    duration = get_audio_duration(file_path)
    estimate = None
    if duration:
        # 根据请求决定预估使用的引擎
        if request.force_engine == "sensevoice":
            provider = "sensevoice"
        elif request.force_engine == "whisper":
            provider = "whisper"
        else:
            # 自动检测语言来决定预估
            from core.smart_transcriber import SmartTranscriber
            temp_episode = PodcastEpisode(
                title=file_path.name,
                audio_url="",
                local_audio_path=file_path,
            )
            detection = SmartTranscriber().detect_language_only(temp_episode)
            provider = detection.get("engine", "whisper")

        estimate = calculate_estimate_time(duration, provider)
        logger.info(
            "音频时长检测完成",
            duration_seconds=duration,
            estimate_seconds=estimate["total_seconds"],
            provider=provider,
            force_engine=request.force_engine,
        )

    # Create job
    jobs[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "file_path": str(file_path),
        "result": None,
        "error": None,
        "error_category": None,
        "estimate": estimate,
        "start_time": time.time(),
    }

    # Start transcription in background with smart routing
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        transcribe_executor,
        _do_transcription,
        task_id,
        file_path,
        file_path.name,
        request.force_engine,
    )

    return TranscribeResponse(task_id=task_id, status="processing", estimate=estimate)


@router.get("/{task_id}", response_model=TranscribeStatusResponse)
async def get_transcription_status(task_id: str):
    """Get transcription status.

    Args:
        task_id: Task ID from start_transcription

    Returns:
        Transcription status and result
    """
    if task_id not in jobs:
        raise HTTPException(status_code=404, detail="Task not found")

    job = jobs[task_id]

    # 计算动态剩余时间
    elapsed = None
    remaining = None
    if job.get("start_time") and job["status"] == "processing":
        elapsed = time.time() - job["start_time"]
        if job.get("estimate"):
            total_estimate = job["estimate"]["total_seconds"]
            remaining = max(0, total_estimate - elapsed)

    return TranscribeStatusResponse(
        task_id=task_id,
        status=job["status"],
        progress=job.get("progress"),
        stage=job.get("stage"),
        result=job.get("result"),
        error=job.get("error"),
        error_category=job.get("error_category"),
        error_detail=job.get("error_detail"),
        estimate=job.get("estimate"),
        elapsed_seconds=round(elapsed, 1) if elapsed else None,
        remaining_seconds=round(remaining, 1) if remaining else None,
    )
