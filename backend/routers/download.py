"""Download router for podcast audio files."""

from __future__ import annotations

import asyncio
import errno
import platform
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.audio_downloader import AudioDownloader
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 线程池用于执行同步下载操作
download_executor = ThreadPoolExecutor(max_workers=3)

# In-memory job storage (replace with Redis/DB in production)
jobs: dict[str, dict] = {}


class DownloadErrorCategory:
    """下载错误分类."""

    NETWORK_ERROR = "network_error"
    RSS_PARSE_ERROR = "rss_parse_error"
    STORAGE_ERROR = "storage_error"
    PERMISSION_ERROR = "permission_error"
    NOT_FOUND_ERROR = "not_found_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


def _categorize_error(error: Exception) -> tuple[str, str]:
    """将异常分类为可处理的错误类型."""
    error_msg = str(error).lower()

    # RSS 解析错误
    if "rss" in error_msg or "feed" in error_msg or "parse" in error_msg:
        return DownloadErrorCategory.RSS_PARSE_ERROR, f"RSS 解析失败: {error}"

    # 网络连接错误
    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
        return DownloadErrorCategory.NETWORK_ERROR, "网络连接失败，请检查网络后重试"

    # HTTP 错误
    if isinstance(error, requests.HTTPError):
        status = error.response.status_code if hasattr(error, "response") and error.response else 0
        if status == 404:
            return DownloadErrorCategory.NOT_FOUND_ERROR, "音频文件在服务器上不存在 (404)"
        elif status >= 500:
            return DownloadErrorCategory.NETWORK_ERROR, f"音频服务器错误 ({status})，请稍后重试"
        return DownloadErrorCategory.NETWORK_ERROR, f"下载请求失败: HTTP {status}"

    # 操作系统错误（文件系统相关）
    if isinstance(error, OSError):
        if error.errno == errno.ENOSPC:
            return DownloadErrorCategory.STORAGE_ERROR, "磁盘空间不足，请清理后重试"
        elif error.errno in (errno.EACCES, errno.EPERM):
            return DownloadErrorCategory.PERMISSION_ERROR, "文件权限不足，无法写入下载目录"
        elif error.errno == errno.ENOENT:
            return DownloadErrorCategory.NOT_FOUND_ERROR, "下载目录不存在"

    # 超时错误
    if "timeout" in error_msg or "timed out" in error_msg:
        return DownloadErrorCategory.TIMEOUT_ERROR, "下载超时，请检查网络后重试"

    # 存储空间错误
    if "no space" in error_msg or "disk full" in error_msg:
        return DownloadErrorCategory.STORAGE_ERROR, "磁盘空间不足"

    # 权限错误
    if "permission" in error_msg or "access" in error_msg:
        return DownloadErrorCategory.PERMISSION_ERROR, "权限不足，无法写入下载目录"

    return DownloadErrorCategory.UNKNOWN_ERROR, f"下载失败: {error}"


class DownloadRequest(BaseModel):
    """Download request model."""

    rss_url: str
    episode_index: int = 0


class DownloadResponse(BaseModel):
    """Download response model."""

    task_id: str
    status: str


class DownloadStatusResponse(BaseModel):
    """Download status response model."""

    task_id: str
    status: str
    progress: float | None = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    result: dict | None = None
    error: str | None = None
    error_category: str | None = None


class RetryRequest(BaseModel):
    """Retry download request model."""

    task_id: str


class BatchDownloadRequest(BaseModel):
    """Batch download request model."""

    rss_url: str
    episode_indices: list[int]


class BatchDownloadResponse(BaseModel):
    """Batch download response model."""

    batch_id: str
    task_ids: list[str]
    total: int


class OpenFolderResponse(BaseModel):
    """Open folder response model."""

    success: bool
    message: str
    file_path: str | None = None


def update_progress(task_id: str, progress: float, downloaded: int, total: int):
    """更新下载进度."""
    if task_id in jobs:
        jobs[task_id]["progress"] = progress
        jobs[task_id]["downloaded_bytes"] = downloaded
        jobs[task_id]["total_bytes"] = total


@router.post("/", response_model=DownloadResponse)
async def start_download(request: DownloadRequest):
    """Start a download task."""
    task_id = str(uuid.uuid4())

    jobs[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "result": None,
        "error": None,
        "error_category": None,
        "rss_url": request.rss_url,
        "episode_index": request.episode_index,
        "created_at": time.time(),
    }

    # 在后台线程中执行下载
    asyncio.create_task(_do_download(task_id, request))

    return DownloadResponse(task_id=task_id, status="processing")


async def _do_download(task_id: str, request: DownloadRequest):
    """后台执行下载任务."""
    try:
        jobs[task_id]["status"] = "processing"

        def progress_cb(progress: float, downloaded: int, total: int):
            update_progress(task_id, progress, downloaded, total)

        # 在线程池中执行同步下载
        loop = asyncio.get_event_loop()
        downloader = AudioDownloader()

        episode, local_path = await loop.run_in_executor(
            download_executor,
            lambda: downloader.download_from_rss(
                rss_url=request.rss_url,
                episode_index=request.episode_index,
                progress_callback=progress_cb,
            )
        )

        jobs[task_id]["status"] = "completed"
        jobs[task_id]["progress"] = 100.0
        jobs[task_id]["result"] = {
            "file_path": str(local_path),
            "file_name": local_path.name,
            "file_size_mb": round(local_path.stat().st_size / 1024 / 1024, 2),
            "episode_title": episode.title,
            "podcast_name": episode.feed_title or "未知播客",
            "duration_seconds": episode.duration_seconds,
        }

    except Exception as e:
        category, message = _categorize_error(e)
        logger.error("Download failed", error=message, category=category, task_id=task_id)
        jobs[task_id]["status"] = "failed"
        jobs[task_id]["error"] = message
        jobs[task_id]["error_category"] = category


@router.get("/{task_id}", response_model=DownloadStatusResponse)
async def get_download_status(task_id: str):
    """Get download task status."""
    if task_id not in jobs:
        raise HTTPException(status_code=404, detail="Task not found")

    job = jobs[task_id]
    return DownloadStatusResponse(
        task_id=task_id,
        status=job["status"],
        progress=job.get("progress"),
        downloaded_bytes=job.get("downloaded_bytes"),
        total_bytes=job.get("total_bytes"),
        result=job.get("result"),
        error=job.get("error"),
        error_category=job.get("error_category"),
    )


@router.post("/retry", response_model=DownloadResponse)
async def retry_download(request: RetryRequest):
    """重试失败的下载任务."""
    if request.task_id not in jobs:
        raise HTTPException(status_code=404, detail="Task not found")

    job = jobs[request.task_id]
    if job["status"] not in ["failed", "error"]:
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    # 重置状态
    jobs[request.task_id]["status"] = "pending"
    jobs[request.task_id]["progress"] = 0.0
    jobs[request.task_id]["error"] = None
    jobs[request.task_id]["error_category"] = None

    # 重新启动下载
    retry_req = DownloadRequest(
        rss_url=job["rss_url"],
        episode_index=job["episode_index"],
    )
    asyncio.create_task(_do_download(request.task_id, retry_req))

    return DownloadResponse(task_id=request.task_id, status="processing")


@router.post("/batch", response_model=BatchDownloadResponse)
async def batch_download(request: BatchDownloadRequest):
    """批量下载多个单集."""
    task_ids = []

    for idx in request.episode_indices:
        task_id = str(uuid.uuid4())
        jobs[task_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "error_category": None,
            "rss_url": request.rss_url,
            "episode_index": idx,
            "created_at": time.time(),
        }

        download_req = DownloadRequest(
            rss_url=request.rss_url,
            episode_index=idx,
        )
        asyncio.create_task(_do_download(task_id, download_req))
        task_ids.append(task_id)

    batch_id = str(uuid.uuid4())
    return BatchDownloadResponse(
        batch_id=batch_id,
        task_ids=task_ids,
        total=len(task_ids),
    )


@router.get("/history/list")
async def get_download_history(limit: int = 20):
    """获取下载历史记录."""
    # 按创建时间倒序排列
    sorted_jobs = sorted(
        jobs.items(),
        key=lambda x: x[1].get("created_at", 0),
        reverse=True,
    )[:limit]

    history = []
    for task_id, job in sorted_jobs:
        history.append({
            "task_id": task_id,
            "status": job["status"],
            "progress": job.get("progress"),
            "episode_title": job.get("result", {}).get("episode_title", "未知单集"),
            "podcast_name": job.get("result", {}).get("podcast_name", "未知播客"),
            "file_size_mb": job.get("result", {}).get("file_size_mb"),
            "created_at": job.get("created_at"),
            "error": job.get("error"),
            "error_category": job.get("error_category"),
        })

    return {"history": history}


@router.post("/open-folder/{task_id}", response_model=OpenFolderResponse)
async def open_download_folder(task_id: str):
    """打开下载文件所在文件夹并高亮显示文件."""
    if task_id not in jobs:
        raise HTTPException(status_code=404, detail="下载任务不存在")

    job = jobs[task_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="文件尚未下载完成")

    result = job.get("result")
    if not result or "file_path" not in result:
        raise HTTPException(status_code=404, detail="未找到文件路径信息")

    file_path = Path(result["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"文件已被移动或删除，请重新下载。原路径: {file_path}"
        )

    try:
        system = platform.system()

        if system == "Windows":
            # Windows: explorer /select,"path" — 必须作为单个字符串传递
            cmd = f'explorer /select,"{str(file_path)}"'
            subprocess.Popen(cmd, shell=True)

        elif system == "Darwin":
            # macOS: open -R path 可以打开文件夹并高亮文件
            subprocess.Popen(['open', '-R', str(file_path)])

        elif system == "Linux":
            # Linux: xdg-open 打开文件夹（无法直接高亮文件）
            folder_path = file_path.parent
            subprocess.Popen(['xdg-open', str(folder_path)])

        else:
            raise HTTPException(
                status_code=500,
                detail=f"不支持的操作系统: {system}"
            )

        return OpenFolderResponse(
            success=True,
            message="已打开文件夹",
            file_path=str(file_path),
        )

    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="权限不足，请检查文件夹访问权限"
        )
    except Exception as e:
        logger.error("打开文件夹失败", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=500,
            detail=f"打开文件夹失败，请手动前往: {file_path}"
        )
