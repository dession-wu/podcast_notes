# MVP Implementation Plan

## Overview
Build a FastAPI backend to expose existing Python modules as HTTP APIs, then integrate them into the Next.js frontend.

## Architecture

```
Frontend (Next.js 16)          Backend (FastAPI)
    localhost:3000    <----->    localhost:8000
         |                            |
    fetch('/api/...')            Python modules
         |                       (podcast_search,
         |                        content_processor,
         |                        transcriber)
    Next.js API Routes           FastAPI Routers
    (proxy to backend)           (CORS enabled)
```

## Implementation Steps

### Step 1: Create FastAPI Backend Structure

Create `backend/` directory with:
- `backend/__init__.py`
- `backend/main.py` - FastAPI app with CORS
- `backend/routers/__init__.py`
- `backend/routers/health.py`
- `backend/routers/search.py`
- `backend/routers/process.py`
- `backend/routers/transcribe.py`

### Step 2: Implement API Endpoints

**Health Check**
- `GET /api/health` → `{status: "ok", services: {...}}`

**Podcast Search**
- `POST /api/search`
- Request: `{term: string, max_results?: number}`
- Response: `{success: boolean, results: PodcastResult[], count: number}`

**Content Processing**
- `POST /api/process`
- Request: `{transcript_text: string, template?: string}`
- Response: `{success: boolean, note: {title, content, tags}}`

**Transcription**
- `POST /api/transcribe` (multipart/form-data)
- Request: audio file upload
- Response: `{task_id: string, status: string}`
- `GET /api/transcribe/{task_id}`
- Response: `{status: string, progress?: number, result?: Transcript}`

### Step 3: Frontend Integration

Create `web-dashboard/src/lib/api.ts`:
- API client with base URL configuration
- Error handling wrapper
- Type definitions

Update Dashboard pages:
- `search/page.tsx` - Replace mock with real API call
- `content/page.tsx` - Replace mock with real API call
- `transcripts/page.tsx` - Add file upload + polling

### Step 4: Environment Configuration

Add to `.env`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 5: Testing

- Start backend: `python -m backend.main`
- Start frontend: `npm run dev`
- Test each endpoint
- Verify build passes

## File Changes

### New Files
- `backend/main.py`
- `backend/routers/*.py`
- `web-dashboard/src/lib/api.ts`

### Modified Files
- `web-dashboard/src/app/dashboard/search/page.tsx`
- `web-dashboard/src/app/dashboard/content/page.tsx`
- `web-dashboard/src/app/dashboard/transcripts/page.tsx`

## Dependencies

Backend:
- fastapi
- uvicorn
- python-multipart

Already available in project:
- pydantic
- httpx
- python-dotenv
