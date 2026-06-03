"""Library router for unified file management."""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.config.download_settings import download_settings_manager
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


class LibraryFile(BaseModel):
    """Unified file item in library."""

    id: str
    name: str
    type: str  # "audio" | "transcript" | "image"
    podcast_name: str
    episode_title: str
    size_mb: float
    created_at: str
    file_path: str
    status: str = "completed"


class LibraryFilesResponse(BaseModel):
    """Library files list response."""

    files: list[LibraryFile]
    total: int
    type_counts: dict[str, int]


def _get_data_dir() -> Path:
    """Get the effective data directory."""
    ds = download_settings_manager.load()
    return ds.get_effective_download_dir().parent


def _scan_directory(
    directory: Path,
    file_type: str,
    search: str,
    time_range: str,
) -> list[LibraryFile]:
    """Scan a directory and return matching files."""
    files: list[LibraryFile] = []

    if not directory.exists():
        return files

    now = datetime.now()
    range_cutoff: datetime | None = None
    if time_range == "today":
        range_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "week":
        range_cutoff = now - timedelta(days=7)
    elif time_range == "month":
        range_cutoff = now - timedelta(days=30)

    for entry in directory.iterdir():
        if not entry.is_file():
            continue

        stat = entry.stat()
        created_dt = datetime.fromtimestamp(stat.st_mtime)

        if range_cutoff and created_dt < range_cutoff:
            continue

        name = entry.name
        if search and search.lower() not in name.lower():
            continue

        size_mb = round(stat.st_size / (1024 * 1024), 2)

        # Parse podcast/episode info from filename
        # Expected formats:
        # audio: "podcast_name - episode_title.mp3"
        # transcript: "podcast_name - episode_title_transcript.txt"
        # image: "podcast_name - episode_title_image_1.png"
        podcast_name = "未知播客"
        episode_title = name

        if " - " in name:
            parts = name.split(" - ", 1)
            podcast_name = parts[0]
            episode_title = parts[1]
            # Remove suffixes like _transcript, _image_1, file extension
            for suffix in ["_transcript", "_image"]:
                if suffix in episode_title:
                    episode_title = episode_title.split(suffix)[0]
            # Remove file extension
            episode_title = Path(episode_title).stem

        files.append(
            LibraryFile(
                id=f"{file_type}_{entry.stem}_{stat.st_mtime}",
                name=name,
                type=file_type,
                podcast_name=podcast_name,
                episode_title=episode_title,
                size_mb=size_mb,
                created_at=created_dt.isoformat(),
                file_path=str(entry.resolve()),
            )
        )

    return files


@router.get("/files", response_model=LibraryFilesResponse)
async def get_library_files(
    type: str = Query("all", description="Filter by type: all, audio, transcript, image"),
    search: str = Query("", description="Search keyword"),
    sort: str = Query("time_desc", description="Sort: time_desc, time_asc, name, size"),
    time_range: str = Query("all", description="Time range: all, today, week, month"),
):
    """Get unified library files with filtering and sorting."""
    data_dir = _get_data_dir()

    type_dirs = {
        "audio": data_dir / "audio",
        "transcript": data_dir / "transcripts",
        "image": data_dir / "images",
    }

    # Always scan ALL directories for accurate type_counts
    all_files_for_counts: list[LibraryFile] = []
    for ft, dir_path in type_dirs.items():
        all_files_for_counts.extend(_scan_directory(dir_path, ft, search, time_range))

    # Calculate type_counts from complete scan
    type_counts = {"audio": 0, "transcript": 0, "image": 0}
    for f in all_files_for_counts:
        if f.type in type_counts:
            type_counts[f.type] += 1

    # Filter files based on type parameter for response
    if type == "all":
        filtered_files = all_files_for_counts
    elif type in type_dirs:
        filtered_files = [f for f in all_files_for_counts if f.type == type]
    else:
        filtered_files = []

    # Sort filtered files
    if sort == "time_desc":
        filtered_files.sort(key=lambda f: f.created_at, reverse=True)
    elif sort == "time_asc":
        filtered_files.sort(key=lambda f: f.created_at)
    elif sort == "name":
        filtered_files.sort(key=lambda f: f.name.lower())
    elif sort == "size":
        filtered_files.sort(key=lambda f: f.size_mb, reverse=True)

    return LibraryFilesResponse(
        files=filtered_files,
        total=len(filtered_files),
        type_counts=type_counts,
    )


class OpenFileRequest(BaseModel):
    """Open file location request."""

    file_path: str


class OpenFileResponse(BaseModel):
    """Open file location response."""

    success: bool
    message: str


class TranscriptContentResponse(BaseModel):
    """Transcript file content response."""

    file_id: str
    file_name: str
    content: str
    word_count: int


@router.post("/open-file", response_model=OpenFileResponse)
async def open_file_location(request: OpenFileRequest):
    """Open the folder containing the specified file and highlight it."""
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        system = platform.system()

        if system == "Windows":
            cmd = f'explorer /select,"{str(file_path)}"'
            subprocess.Popen(cmd, shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", "-R", str(file_path)])
        elif system == "Linux":
            folder_path = file_path.parent
            subprocess.Popen(["xdg-open", str(folder_path)])
        else:
            raise HTTPException(status_code=500, detail=f"不支持的操作系统: {system}")

        return OpenFileResponse(success=True, message="已打开文件夹")

    except PermissionError:
        raise HTTPException(status_code=403, detail="权限不足")
    except Exception as e:
        logger.error("打开文件夹失败", error=str(e), file_path=str(file_path))
        raise HTTPException(status_code=500, detail=f"打开文件夹失败: {e}")


@router.get("/transcript-content/{file_id}", response_model=TranscriptContentResponse)
async def get_transcript_content(file_id: str):
    """读取转录文件（.md 或 .txt）的文本内容。"""
    data_dir = _get_data_dir()
    transcripts_dir = data_dir / "transcripts"

    if not transcripts_dir.exists():
        raise HTTPException(status_code=404, detail="Transcripts directory not found")

    # 查找匹配的文件（file_id 格式: transcript_{stem}_{mtime}）
    for entry in transcripts_dir.iterdir():
        if entry.is_file():
            stat = entry.stat()
            entry_id = f"transcript_{entry.stem}_{stat.st_mtime}"
            if entry_id == file_id:
                try:
                    content = entry.read_text(encoding="utf-8")
                    return TranscriptContentResponse(
                        file_id=file_id,
                        file_name=entry.name,
                        content=content,
                        word_count=len(content),
                    )
                except Exception as e:
                    logger.error("读取转录文件失败", error=str(e), file_id=file_id)
                    raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    raise HTTPException(status_code=404, detail="Transcript file not found")
