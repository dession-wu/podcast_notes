"""Image generation router for Xiaohongshu notes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.image_generator import ImageGenerator
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

# In-memory job storage
jobs: dict[str, dict] = {}


class ImageGenerateRequest(BaseModel):
    """Image generation request model."""

    title: str
    content: str
    tags: list[str] = []
    podcast_name: str = ""
    episode_title: str = ""
    style: str = "blue"
    template: str = "v9"


class ImageGenerateResponse(BaseModel):
    """Image generation response model."""

    task_id: str
    status: str


class ImageStatusResponse(BaseModel):
    """Image generation status response model."""

    task_id: str
    status: str
    progress: float | None = None
    result: dict | None = None
    error: str | None = None


@router.post("/", response_model=ImageGenerateResponse)
async def start_image_generation(request: ImageGenerateRequest):
    """Start generating images for a Xiaohongshu note.

    Args:
        request: Image generation request with note content

    Returns:
        Image generation response with task_id
    """
    try:
        task_id = str(uuid.uuid4())

        # Create job
        jobs[task_id] = {
            "status": "processing",
            "progress": 10.0,
            "result": None,
            "error": None,
        }

        # Prepare structured content based on template
        if request.template == "v9":
            structured_content = {
                "hook_title": request.title,
                "thinking": request.content,
                "tags": request.tags,
            }
        else:
            structured_content = {
                "hook_title": request.title,
                "thinking": request.content,
                "tags": request.tags,
                "key_points": [{"title": p} for p in request.content.split("\n") if p.strip()][:5],
            }

        source_info = {
            "podcast_name": request.podcast_name,
            "episode_title": request.episode_title,
        }

        # Generate images
        generator = ImageGenerator()
        image_paths = await generator.generate_note_images(
            structured_content=structured_content,
            source_info=source_info,
            style=request.style,
        )

        # Convert paths to URLs
        image_urls = []
        for i, path in enumerate(image_paths):
            image_urls.append({
                "id": f"{task_id}_{i}",
                "path": str(path),
                "name": path.name,
                "index": i,
            })

        # Update job
        jobs[task_id]["status"] = "completed"
        jobs[task_id]["progress"] = 100.0
        jobs[task_id]["result"] = {
            "images": image_urls,
            "count": len(image_urls),
        }

        return ImageGenerateResponse(task_id=task_id, status="completed")

    except Exception as e:
        logger.error("Image generation failed", error=str(e))
        if "task_id" in locals():
            jobs[task_id]["status"] = "failed"
            jobs[task_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.get("/{task_id}", response_model=ImageStatusResponse)
async def get_image_status(task_id: str):
    """Get image generation status.

    Args:
        task_id: Task ID from start_image_generation

    Returns:
        Image generation status and result
    """
    if task_id not in jobs:
        raise HTTPException(status_code=404, detail="Task not found")

    job = jobs[task_id]
    return ImageStatusResponse(
        task_id=task_id,
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
    )
