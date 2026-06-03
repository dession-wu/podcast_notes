"""Podcast search router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.podcast_search import PodcastSearcher
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model."""

    term: str
    max_results: int = 10


class SearchResult(BaseModel):
    """Search result model."""

    id: str
    title: str
    author: str
    description: str
    episode_count: int
    rss_url: str
    image_url: str | None = None
    website: str | None = None


class SearchResponse(BaseModel):
    """Search response model."""

    success: bool
    results: list[SearchResult]
    count: int
    source: str


@router.post("/", response_model=SearchResponse)
async def search_podcasts(request: SearchRequest):
    """Search for podcasts by term.

    Args:
        request: Search request with term and max_results

    Returns:
        Search response with podcast results
    """
    try:
        searcher = PodcastSearcher()
        results = await searcher.search(request.term, max_results=request.max_results)

        # Convert to response model
        search_results = []
        for i, result in enumerate(results):
            search_results.append(
                SearchResult(
                    id=result.id or str(i + 1),
                    title=result.title,
                    author=result.author or result.title,
                    description=result.description or "",
                    episode_count=result.episode_count or 0,
                    rss_url=result.rss_url,
                    image_url=result.image_url,
                    website=result.website,
                )
            )

        # Determine source from results
        sources = list(set(r.source for r in results if r.source))
        source = sources[0] if sources else "unknown"

        return SearchResponse(
            success=True,
            results=search_results,
            count=len(search_results),
            source=source,
        )

    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
