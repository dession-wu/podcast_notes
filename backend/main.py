"""FastAPI application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import health, search, process, transcribe, download, images, episodes, settings as settings_router, library as library_router, analyze

app = FastAPI(
    title="Podcast Notes API",
    description="Backend API for Podcast Notes Platform",
    version="0.1.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
        "http://localhost:3004",
        "http://127.0.0.1:3004",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(process.router, prefix="/api/process", tags=["process"])
app.include_router(transcribe.router, prefix="/api/transcribe", tags=["transcribe"])
app.include_router(download.router, prefix="/api/download", tags=["download"])
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(library_router.router, prefix="/api/library", tags=["library"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["analyze"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Podcast Notes API",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
