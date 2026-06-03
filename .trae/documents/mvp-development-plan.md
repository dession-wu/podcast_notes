# MVP Development Plan — Podcast Notes Platform

> **Date**: 2026-05-27
> **Scope**: Backend API layer + Frontend integration for core features
> **Goal**: Make Dashboard functional with real data flow

---

## 1. Current State Summary

### What Works (Python Backend)
- `podcast_search.py` — Multi-source podcast search (PodcastIndex → iTunes → ListenNotes)
- `content_processor.py` — LLM-powered content extraction & Xiaohongshu note generation
- `transcriber.py` — Speech-to-text with SenseVoice/Whisper/Faster-Whisper
- `llm_service.py` — Unified LLM wrapper (OpenAI / Anthropic / Ollama)
- `image_generator.py` — HTML template → PNG rendering

### What Doesn't Work (Frontend)
- All Dashboard pages use **mock data** with `setTimeout()` simulation
- **Zero API calls** to backend (except download)
- No HTTP server exposing Python functionality

### Architecture Gap
```
Frontend (Next.js)          Backend (Python)
    ↓                            ↓
Mock Data ←──────×──────→ CLI Modules
(setTimeout)              (No HTTP API)
```

---

## 2. MVP Scope

### Core Features (Priority Order)

| # | Feature | Backend Module | Frontend Page | Complexity |
|---|---------|---------------|---------------|------------|
| 1 | **Podcast Search** | `podcast_search.py` | `dashboard/search` | Low |
| 2 | **Content Processing** | `content_processor.py` | `dashboard/content` | Medium |
| 3 | **Transcription** | `transcriber.py` | `dashboard/transcripts` | High |

### Out of MVP Scope
- Image generation (v7 visual templates) — requires Playwright, heavy
- Publishing to Xiaohongshu — requires RPA/browser automation
- User authentication — simplified localStorage token
- Download queue management — single-file download only

---

## 3. Technical Architecture

### 3.1 Backend: FastAPI Service

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Podcast Notes API")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(transcribe.router, prefix="/api/transcribe", tags=["transcribe"])
app.include_router(process.router, prefix="/api/process", tags=["process"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
```

### 3.2 API Endpoints

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/api/health` | GET | — | `{status, version, services}` | Health check |
| `/api/search` | POST | `{term, max_results}` | `{success, results[], count}` | Podcast search |
| `/api/transcribe` | POST | `multipart/form-data` (audio) | `{task_id, status}` | Start transcription |
| `/api/transcribe/{id}` | GET | — | `{status, progress, result}` | Check transcription |
| `/api/process` | POST | `{transcript_text, template}` | `{title, content, tags}` | Generate note |

### 3.3 Frontend Integration

Replace mock handlers with `fetch()` calls:

```typescript
// Before (Mock)
const handleSearch = async () => {
  setIsSearching(true);
  await new Promise(r => setTimeout(r, 1500));
  setResults(mockResults); // ← hardcoded
  setIsSearching(false);
};

// After (Real API)
const handleSearch = async () => {
  setIsSearching(true);
  const res = await fetch('/api/search', {
    method: 'POST',
    body: JSON.stringify({ term: query })
  });
  const data = await res.json();
  setResults(data.results); // ← real data
  setIsSearching(false);
};
```

---

## 4. Implementation Phases

### Phase 1: FastAPI Backend Scaffold (Day 1)

**Tasks**:
1. Create `backend/` directory structure
2. Install FastAPI + Uvicorn dependencies
3. Create `backend/main.py` with CORS and health endpoint
4. Add startup script `python -m backend.main`
5. Verify backend starts on `http://localhost:8000`

**Deliverable**: Running FastAPI server with `/api/health` returning 200

**Files**:
- `backend/main.py`
- `backend/requirements.txt` (fastapi, uvicorn, python-multipart)
- `backend/routers/__init__.py`
- `backend/routers/health.py`

---

### Phase 2: Podcast Search API (Day 1-2)

**Tasks**:
1. Create `backend/routers/search.py`
2. Import `PodcastSearcher` from `services/podcast_search`
3. Implement `POST /api/search` endpoint
4. Handle PodcastIndex auth from environment variables
5. Test with curl/Postman

**Deliverable**: `curl -X POST http://localhost:8000/api/search -d '{"term":"知行小酒馆"}'` returns real results

**Files**:
- `backend/routers/search.py`

**Frontend Changes**:
- `dashboard/search/page.tsx`: Replace mock with `fetch('/api/search')`

---

### Phase 3: Content Processing API (Day 2-3)

**Tasks**:
1. Create `backend/routers/process.py`
2. Import `ContentProcessor` and `LLMService`
3. Implement `POST /api/process` endpoint
4. Accept `transcript_text` + `template_name` in request body
5. Return generated note (title, content, tags)
6. Handle LLM configuration from `.env`

**Deliverable**: API returns AI-generated Xiaohongshu notes from transcript text

**Files**:
- `backend/routers/process.py`

**Frontend Changes**:
- `dashboard/content/page.tsx`: Replace mock with `fetch('/api/process')`
- Add text area for direct transcript input (MVP simplification)

---

### Phase 4: Transcription API (Day 3-5)

**Tasks**:
1. Create `backend/routers/transcribe.py`
2. Implement file upload endpoint (`multipart/form-data`)
3. Integrate `Transcriber` with SenseVoice
4. Implement async job pattern:
   - `POST /api/transcribe` → returns `task_id`
   - `GET /api/transcribe/{task_id}` → returns progress/result
5. Store uploaded files to `data/temp/`
6. Save transcripts to `data/transcripts/`

**Challenge**: SenseVoice model loading is slow (~10-30s first time)
**Solution**: Load model at startup, keep in memory

**Deliverable**: Upload audio file → receive transcription text

**Files**:
- `backend/routers/transcribe.py`
- `backend/models/job.py` (simple in-memory job tracking)

**Frontend Changes**:
- `dashboard/transcripts/page.tsx`: Add file upload UI
- Show transcription progress

---

### Phase 5: Frontend Integration & Polish (Day 5-6)

**Tasks**:
1. Update all Dashboard pages to use real API calls
2. Add loading states and error handling
3. Remove `DevBanner` from functional pages
4. Update Dashboard home stats to reflect real data
5. Add API base URL configuration (`NEXT_PUBLIC_API_URL`)

**Deliverable**: All core features work end-to-end

---

### Phase 6: Testing & Verification (Day 6-7)

**Tasks**:
1. Test podcast search with various queries
2. Test content processing with real transcripts
3. Test audio upload and transcription
4. Verify error handling (network errors, API failures)
5. Run `npm run build` to ensure no TypeScript errors
6. Document API usage

**Deliverable**: Working MVP with test results

---

## 5. File Structure

```
podcast_notes/
├── backend/                    # NEW: FastAPI backend
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   ├── requirements.txt        # Backend deps
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py           # Health check
│   │   ├── search.py           # Podcast search
│   │   ├── process.py          # Content processing
│   │   └── transcribe.py       # Audio transcription
│   └── models/
│       └── job.py              # Async job tracking
│
├── web-dashboard/              # EXISTING: Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/            # Keep existing routes
│   │   │   └── dashboard/
│   │   │       ├── search/
│   │   │       │   └── page.tsx    # UPDATE: real API
│   │   │       ├── content/
│   │   │       │   └── page.tsx    # UPDATE: real API
│   │   │       └── transcripts/
│   │   │           └── page.tsx    # UPDATE: upload + API
│   │   └── lib/
│   │       └── api.ts          # NEW: API client utilities
│   └── .env.local              # NEW: API_URL config
│
├── core/                       # EXISTING: Python modules
│   ├── content_processor.py
│   ├── transcriber.py
│   └── image_generator.py
│
├── services/                   # EXISTING: Python services
│   ├── podcast_search.py
│   ├── llm_service.py
│   └── ...
│
└── .env                        # EXISTING: API keys config
```

---

## 6. Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PODCASTINDEX_API_KEY` | PodcastIndex API Key | `D4AD6GWM6ASG5QDDFGRL` |
| `PODCASTINDEX_API_SECRET` | PodcastIndex API Secret | `QwHWCzXV7XaJ84wzj9NLVfruPcEqGWQNnRvYEYdW` |
| `OLLAMA_HOST` | Ollama service URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen2.5:14b` |
| `STT_PROVIDER` | Speech-to-text engine | `sensevoice` |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL | `http://localhost:8000` |

### Startup Commands

```bash
# Terminal 1: Start backend
cd d:\podcast_notes
python -m backend.main
# → http://localhost:8000

# Terminal 2: Start frontend
cd d:\podcast_notes\web-dashboard
npm run dev
# → http://localhost:3000
```

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| SenseVoice model loading slow | High | Pre-load at startup; show progress UI |
| LLM service unavailable | High | Graceful fallback; clear error messages |
| PodcastIndex API limits | Low | Multi-source fallback already implemented |
| CORS issues | Medium | Proper CORS config; env-based origins |
| File upload size limits | Medium | Configure max size; add validation |

---

## 8. Acceptance Criteria

### Feature 1: Podcast Search
- [ ] User can search by podcast name
- [ ] Results show real podcasts from PodcastIndex/iTunes
- [ ] Each result displays title, author, description, episode count
- [ ] Loading state during search
- [ ] Error handling for API failures

### Feature 2: Content Processing
- [ ] User can input transcript text
- [ ] Select template (v1-v9)
- [ ] Click "Generate" triggers LLM processing
- [ ] Result shows title, content, tags
- [ ] Copy to clipboard works

### Feature 3: Transcription
- [ ] User can upload audio file (MP3/WAV/M4A)
- [ ] Progress indicator during transcription
- [ ] Result displays transcript text
- [ ] Transcript saved to local storage
- [ ] Error handling for unsupported formats

---

## 9. Success Metrics

- **Functional**: All 3 core features work end-to-end
- **Performance**: API response < 3s (search), < 30s (transcription)
- **Reliability**: No unhandled errors; graceful degradation
- **Quality**: `npm run build` passes; no TypeScript errors

---

## 10. Post-MVP Roadmap

| Phase | Features | Timeline |
|-------|----------|----------|
| MVP+1 | Image generation (v7 templates) | +3 days |
| MVP+2 | Download queue + batch processing | +2 days |
| MVP+3 | User auth + settings persistence | +3 days |
| MVP+4 | Xiaohongshu publishing (RPA) | +5 days |
| MVP+5 | Database persistence (SQLite/PostgreSQL) | +5 days |
