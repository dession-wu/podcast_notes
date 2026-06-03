# Document Preview & Download Feature — PRD & Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a document preview interface with download capabilities, proofreading integration, and error handling for the podcast-to-notes pipeline.

**Architecture:** A Next.js 15 + React 19 frontend with modular components for preview (Markdown/TXT/JSON rendering), download (multi-format export), and proofreading (LLM-powered grammar check with user review UI). Backend uses existing Python pipeline with new FastAPI-style endpoints (Next.js API routes) for file serving and processing.

**Tech Stack:** Next.js 15 App Router, React 19, Tailwind CSS v4, Framer Motion, lucide-react. Python backend (existing): Pydantic models, Jinja2, Playwright.

---

## 1. Product Requirements Document (PRD)

### 1.1 Functional Requirements

#### FR-1: Document Online Preview
- **FR-1.1:** The system shall display generated documents (transcript `.md`, note `.md`, structured JSON) in a responsive preview panel.
- **FR-1.2:** The preview shall accurately render Markdown formatting (headings, lists, bold, italic, code blocks, blockquotes).
- **FR-1.3:** The preview shall support page/section navigation for long documents.
- **FR-1.4:** The preview shall support zoom controls (75%, 100%, 125%, 150%).
- **FR-1.5:** The preview shall support text search with highlight (Ctrl+F or dedicated search bar).
- **FR-1.6:** The preview shall display image previews inline when present.

#### FR-2: Document Download
- **FR-2.1:** The system shall support downloading documents in multiple formats:
  - **TXT** — Plain text (from transcript or note content)
  - **MD** — Markdown (original format)
  - **JSON** — Structured data (chapters, key_points, quotes, etc.)
  - **PNG** — Generated visual note images (cover + content + summary pages)
- **FR-2.2:** Downloaded files shall maintain original formatting and content integrity.
- **FR-2.3:** File naming convention: `{podcast_name}_{episode_title}_{type}.{ext}` with sanitized characters.
- **FR-2.4:** Download progress shall be indicated for batch/multi-file downloads.
- **FR-2.5:** Batch download shall be available as a ZIP archive containing all generated assets.

#### FR-3: Document Proofreading
- **FR-3.1:** The system shall integrate a preliminary proofreading check before download.
- **FR-3.2:** Proofreading shall detect basic grammar and spelling errors in Chinese text.
- **FR-3.3:** Detected errors shall be displayed with:
  - Error location (line/paragraph)
  - Error type (grammar, spelling, punctuation)
  - Suggested correction
  - Context snippet
- **FR-3.4:** Users shall be able to accept or reject each suggested correction individually.
- **FR-3.5:** Accepted corrections shall be applied to the document before download.
- **FR-3.6:** The proofreading UI shall not block the download flow (non-blocking).

#### FR-4: Error Prevention and Handling
- **FR-4.1:** Pre-conversion validation shall check for:
  - Empty or corrupted transcript files
  - Unsupported character encodings
  - Missing required fields (title, content)
- **FR-4.2:** Post-conversion validation shall verify:
  - Generated file integrity (size > 0, readable)
  - Image generation success (all pages present)
  - JSON schema compliance
- **FR-4.3:** Error logging shall capture:
  - Error type and message
  - File path and processing stage
  - Timestamp and stack trace
- **FR-4.4:** Fallback mechanisms:
  - If image generation fails, allow text-only download
  - If proofreading fails, allow download without corrections
  - If JSON export fails, fallback to Markdown

### 1.2 User Interface Specifications

#### UI-1: Preview Panel Layout
```
┌─────────────────────────────────────────────────────────────┐
│  Header: Document Title + [Preview | Proofread | Download]  │
├─────────────────────────────────────────────────────────────┤
│  Toolbar: [Zoom ▼] [Search 🔍] [Navigate ◀ ▶] [Format ▼]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    Preview Content Area                     │
│              (Markdown-rendered with styles)                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Status Bar: Line count | Word count | Encoding | File size │
└─────────────────────────────────────────────────────────────┘
```

#### UI-2: Download Modal
```
┌─────────────────────────────────────────────┐
│  Download Options                             │
│  ─────────────────────────────────────────  │
│  ☑ Transcript (TXT)     ☑ Note (MD)         │
│  ☑ Structured (JSON)    ☑ Images (PNG ZIP)  │
│                                             │
│  File name: [podcast_episode_title____]     │
│                                             │
│  [Cancel]              [Download All]       │
└─────────────────────────────────────────────┘
```

#### UI-3: Proofreading Sidebar
```
┌─────────────────────────────────────────────────────────────┐
│  Preview Area          │  Proofreading Panel                │
│                        │  ────────────────────────────────  │
│                        │  ⚠ 3 issues found                  │
│                        │  ────────────────────────────────  │
│                        │  1. Line 12: "的" → "地"          │
│                        │     Context: "快速的增长"          │
│                        │     [Accept] [Reject]              │
│                        │  2. Line 45: Missing punctuation   │
│                        │     ...                            │
│                        │  [Apply All] [Ignore All]          │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Technical Constraints

- **TC-1:** Preview must work without server-side rendering (client-side Markdown parsing).
- **TC-2:** Download must use browser-native `Blob` + `URL.createObjectURL` for immediate response.
- **TC-3:** ZIP generation for batch download must use `JSZip` library (client-side).
- **TC-4:** Proofreading must call existing LLM service (`LLMService`) via API route.
- **TC-5:** All file operations must be UTF-8 encoded to prevent Chinese character corruption.
- **TC-6:** Maximum preview file size: 5MB (for performance). Larger files show first 5MB with "Load more".

### 1.4 Acceptance Criteria

| ID | Criteria | Test Method |
|----|----------|-------------|
| AC-1 | User can preview a generated `.md` file with correct formatting | Visual inspection |
| AC-2 | User can download TXT, MD, JSON, PNG formats individually | Functional test |
| AC-3 | Downloaded file name follows `{podcast}_{episode}_{type}.{ext}` | File system check |
| AC-4 | Batch download produces valid ZIP with all selected files | ZIP extraction test |
| AC-5 | Proofreading detects at least 80% of obvious grammar errors | Sample text test |
| AC-6 | User can accept/reject corrections and see updated preview | Interactive test |
| AC-7 | Empty/corrupted files show friendly error message | Error injection test |
| AC-8 | Image generation failure allows text-only download | Failure simulation |

---

## 2. File Structure

### New Files

| File | Responsibility |
|------|----------------|
| `web-dashboard/src/components/DocumentPreview.tsx` | Main preview panel with Markdown rendering, zoom, search |
| `web-dashboard/src/components/PreviewToolbar.tsx` | Zoom, search, navigation, format selector controls |
| `web-dashboard/src/components/DownloadModal.tsx` | Format selection, file naming, download trigger |
| `web-dashboard/src/components/ProofreadPanel.tsx` | Sidebar showing detected errors with accept/reject buttons |
| `web-dashboard/src/components/ErrorToast.tsx` | Non-blocking error notifications |
| `web-dashboard/src/lib/markdownParser.ts` | Client-side Markdown → HTML converter (lightweight) |
| `web-dashboard/src/lib/fileDownloader.ts` | Blob creation, file naming, ZIP generation |
| `web-dashboard/src/app/api/proofread/route.ts` | Next.js API route for LLM proofreading |
| `web-dashboard/src/app/api/download/route.ts` | Next.js API route for file serving |
| `core/document_validator.py` | Pre/post conversion validation logic |
| `core/proofreader.py` | LLM-powered proofreading engine |

### Modified Files

| File | Changes |
|------|---------|
| `web-dashboard/src/app/page.tsx` | Add preview/download/proofread tabs to task detail view |
| `web-dashboard/package.json` | Add `jszip`, `marked` dependencies |
| `models/transcript.py` | Add `to_txt()`, `to_json()` export methods |
| `models/xiaohongshu.py` | Add `to_txt()`, `to_json()` export methods |

---

## 3. Implementation Tasks

### Task 1: Document Export Methods (Backend)

**Files:**
- Modify: `models/transcript.py`
- Modify: `models/xiaohongshu.py`

- [ ] **Step 1: Add `to_txt()` to Transcript model**

```python
def to_txt(self) -> str:
    """Export transcript as plain text."""
    lines = [
        f"Title: {self.episode_title}",
        f"Podcast: {self.podcast_name or 'Unknown'}",
        f"Duration: {self.duration_seconds:.0f}s" if self.duration_seconds else "",
        "",
        "=" * 50,
        "",
    ]
    for seg in self.segments:
        speaker = f"[{seg.speaker}] " if seg.speaker else ""
        lines.append(f"{seg.format_timestamp()} {speaker}{seg.text}")
    return "\n".join(lines)
```

- [ ] **Step 2: Add `to_json()` to Transcript model**

```python
def to_json(self) -> str:
    """Export transcript as structured JSON."""
    return self.model_dump_json(indent=2, ensure_ascii=False)
```

- [ ] **Step 3: Add `to_txt()` to XiaohongshuNote model**

```python
def to_txt(self) -> str:
    """Export note as plain text."""
    lines = [
        self.title,
        "",
        self.content,
        "",
        "Tags: " + " ".join(f"#{t}" for t in self.tags),
        "",
        f"Source: {self.source_podcast or 'Unknown'}",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Add `to_json()` to XiaohongshuNote model**

```python
def to_json(self) -> str:
    """Export note as structured JSON."""
    return self.model_dump_json(indent=2, ensure_ascii=False)
```

- [ ] **Step 5: Run model tests**

Run: `pytest tests/test_models.py -v`
Expected: All existing tests pass, new methods work.

---

### Task 2: Document Validator (Backend)

**Files:**
- Create: `core/document_validator.py`

- [ ] **Step 1: Create validator module**

```python
"""Document validation — pre and post conversion checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models.transcript import Transcript
from models.xiaohongshu import XiaohongshuNote
from utils import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Validation failure."""
    pass


class DocumentValidator:
    """Validates documents before and after conversion."""

    MAX_FILE_SIZE_MB = 50
    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig"]

    @staticmethod
    def pre_conversion_check(file_path: Path) -> dict[str, Any]:
        """Check file before processing.
        
        Returns:
            Dict with 'valid' (bool), 'errors' (list), 'warnings' (list).
        """
        errors = []
        warnings = []

        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > DocumentValidator.MAX_FILE_SIZE_MB:
            errors.append(f"File too large: {size_mb:.1f}MB (max {DocumentValidator.MAX_FILE_SIZE_MB}MB)")

        if size_mb == 0:
            errors.append("File is empty")

        # Try reading with UTF-8
        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                errors.append("File contains no text content")
        except UnicodeDecodeError:
            errors.append("File encoding is not UTF-8. Please convert to UTF-8.")
        except Exception as e:
            errors.append(f"Cannot read file: {e}")

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
        logger.info("Pre-conversion check", file=str(file_path), **result)
        return result

    @staticmethod
    def post_conversion_check(output_dir: Path, expected_files: list[str]) -> dict[str, Any]:
        """Verify generated files exist and are valid.
        
        Returns:
            Dict with 'valid' (bool), 'missing' (list), 'corrupted' (list).
        """
        missing = []
        corrupted = []

        for filename in expected_files:
            file_path = output_dir / filename
            if not file_path.exists():
                missing.append(filename)
                continue
            if file_path.stat().st_size == 0:
                corrupted.append(f"{filename} (empty)")

        result = {
            "valid": len(missing) == 0 and len(corrupted) == 0,
            "missing": missing,
            "corrupted": corrupted,
        }
        logger.info("Post-conversion check", dir=str(output_dir), **result)
        return result
```

- [ ] **Step 2: Write test for validator**

Create: `tests/test_validator.py`

```python
import pytest
from pathlib import Path
from core.document_validator import DocumentValidator

def test_pre_conversion_empty_file(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("")
    result = DocumentValidator.pre_conversion_check(empty)
    assert result["valid"] is False
    assert any("empty" in e.lower() for e in result["errors"])

def test_pre_conversion_valid_file(tmp_path):
    valid = tmp_path / "valid.md"
    valid.write_text("# Hello\n\nThis is content.")
    result = DocumentValidator.pre_conversion_check(valid)
    assert result["valid"] is True
```

- [ ] **Step 3: Run validator tests**

Run: `pytest tests/test_validator.py -v`
Expected: PASS

---

### Task 3: Proofreading Engine (Backend)

**Files:**
- Create: `core/proofreader.py`

- [ ] **Step 1: Create proofreader module**

```python
"""Document proofreading — LLM-powered grammar and spelling check."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from services.llm_service import LLMService
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class ProofreadIssue:
    """A single proofreading issue."""
    line: int
    column: int
    original: str
    suggestion: str
    issue_type: str  # "grammar", "spelling", "punctuation"
    context: str
    accepted: bool | None = None  # None = pending, True = accepted, False = rejected


class Proofreader:
    """Proofreads Chinese text using LLM."""

    SYSTEM_PROMPT = """你是一位中文文档校对专家。请仔细阅读以下文本，找出其中的语法错误、错别字、标点符号错误。

对于每个错误，请按以下 JSON 格式输出：
{
  "issues": [
    {
      "line": 行号,
      "column": 列号,
      "original": "错误文本",
      "suggestion": "建议修改",
      "type": "grammar|spelling|punctuation",
      "context": "包含错误的上下文（30字左右）"
    }
  ]
}

要求：
- 只输出 JSON，不要其他解释
- 重点关注"的/地/得"误用、错别字、标点错误
- 忽略口语化表达（这是播客转录文本）
- 如果没有错误，输出 {"issues": []}"""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm = llm_service or LLMService()

    async def proofread(self, text: str) -> list[ProofreadIssue]:
        """Proofread text and return list of issues."""
        prompt = f"{self.SYSTEM_PROMPT}\n\n文本：\n{text}"
        
        try:
            response = await self.llm.generate(prompt)
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in proofreading response")
                return []
            
            data = json.loads(json_match.group())
            issues = []
            for item in data.get("issues", []):
                issues.append(ProofreadIssue(
                    line=item.get("line", 0),
                    column=item.get("column", 0),
                    original=item.get("original", ""),
                    suggestion=item.get("suggestion", ""),
                    issue_type=item.get("type", "grammar"),
                    context=item.get("context", ""),
                ))
            
            logger.info("Proofreading complete", issues_found=len(issues))
            return issues
        except Exception as e:
            logger.error("Proofreading failed", error=str(e))
            return []

    def apply_corrections(self, text: str, issues: list[ProofreadIssue]) -> str:
        """Apply all accepted corrections to text."""
        corrected = text
        # Sort by position (reverse) to avoid offset issues
        accepted = [i for i in issues if i.accepted is True]
        accepted.sort(key=lambda x: (x.line, x.column), reverse=True)
        
        for issue in accepted:
            corrected = corrected.replace(issue.original, issue.suggestion, 1)
        
        return corrected
```

- [ ] **Step 2: Write test for proofreader**

Create: `tests/test_proofreader.py`

```python
import pytest
from core.proofreader import Proofreader, ProofreadIssue

def test_apply_corrections():
    p = Proofreader()
    text = "快速的成长需要耐心。"
    issues = [
        ProofreadIssue(line=1, column=1, original="快速的", suggestion="快速地", issue_type="grammar", context="快速的成长", accepted=True),
    ]
    result = p.apply_corrections(text, issues)
    assert "快速地" in result
```

- [ ] **Step 3: Run proofreader tests**

Run: `pytest tests/test_proofreader.py -v`
Expected: PASS

---

### Task 4: Install Frontend Dependencies

**Files:**
- Modify: `web-dashboard/package.json`

- [ ] **Step 1: Add dependencies**

```bash
cd web-dashboard && npm install marked jszip @types/marked
```

- [ ] **Step 2: Verify installation**

Check `package.json` contains:
```json
"marked": "^15.0.0",
"jszip": "^3.10.0"
```

---

### Task 5: Markdown Parser Utility

**Files:**
- Create: `web-dashboard/src/lib/markdownParser.ts`

- [ ] **Step 1: Create parser module**

```typescript
import { marked } from 'marked';

export interface ParsedDocument {
  html: string;
  title: string;
  wordCount: number;
  lineCount: number;
}

export function parseMarkdown(content: string): ParsedDocument {
  const html = marked.parse(content, { 
    async: false,
    gfm: true,
    breaks: true,
  }) as string;
  
  const lines = content.split('\n');
  const titleMatch = content.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1] : 'Untitled';
  
  // Count Chinese characters + English words
  const chineseChars = (content.match(/[\u4e00-\u9fff]/g) || []).length;
  const englishWords = (content.match(/[a-zA-Z]+/g) || []).length;
  
  return {
    html,
    title,
    wordCount: chineseChars + englishWords,
    lineCount: lines.length,
  };
}

export function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

---

### Task 6: File Downloader Utility

**Files:**
- Create: `web-dashboard/src/lib/fileDownloader.ts`

- [ ] **Step 1: Create downloader module**

```typescript
import JSZip from 'jszip';

export interface DownloadFile {
  name: string;
  content: string | Blob;
  type: string;
}

export function sanitizeFilename(name: string): string {
  return name
    .replace(/[<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, '_')
    .substring(0, 100);
}

export function downloadFile(file: DownloadFile): void {
  const blob = file.content instanceof Blob 
    ? file.content 
    : new Blob([file.content], { type: file.type });
  
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = file.name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function downloadZip(files: DownloadFile[], zipName: string): Promise<void> {
  const zip = new JSZip();
  
  files.forEach(file => {
    const content = file.content instanceof Blob 
      ? file.content 
      : file.content;
    zip.file(file.name, content);
  });
  
  const blob = await zip.generateAsync({ type: 'blob' });
  downloadFile({ name: zipName, content: blob, type: 'application/zip' });
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
```

---

### Task 7: Preview Toolbar Component

**Files:**
- Create: `web-dashboard/src/components/PreviewToolbar.tsx`

- [ ] **Step 1: Create toolbar component**

```tsx
"use client";

import { ZoomIn, ZoomOut, Search, ChevronLeft, ChevronRight, FileText } from "lucide-react";

interface PreviewToolbarProps {
  zoom: number;
  onZoomChange: (zoom: number) => void;
  onSearch: (query: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  format: string;
  onFormatChange: (format: string) => void;
}

const ZOOM_LEVELS = [75, 100, 125, 150];
const FORMATS = [
  { id: 'markdown', label: 'Markdown', icon: FileText },
  { id: 'text', label: 'Plain Text', icon: FileText },
];

export default function PreviewToolbar({
  zoom,
  onZoomChange,
  onSearch,
  currentPage,
  totalPages,
  onPageChange,
  format,
  onFormatChange,
}: PreviewToolbarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-surface border-b border-border">
      {/* Zoom Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => {
            const idx = ZOOM_LEVELS.indexOf(zoom);
            if (idx > 0) onZoomChange(ZOOM_LEVELS[idx - 1]);
          }}
          disabled={zoom === ZOOM_LEVELS[0]}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
        <button
          onClick={() => {
            const idx = ZOOM_LEVELS.indexOf(zoom);
            if (idx < ZOOM_LEVELS.length - 1) onZoomChange(ZOOM_LEVELS[idx + 1]);
          }}
          disabled={zoom === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>

      {/* Search */}
      <div className="relative flex-1 max-w-xs mx-4">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
        <input
          type="text"
          placeholder="搜索..."
          onChange={(e) => onSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-1.5 bg-surface-subtle border border-border rounded-lg text-sm focus:outline-none focus:border-accent"
        />
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm">
          {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
```

---

### Task 8: Document Preview Component

**Files:**
- Create: `web-dashboard/src/components/DocumentPreview.tsx`

- [ ] **Step 1: Create main preview component**

```tsx
"use client";

import { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { FileText, AlertCircle } from "lucide-react";
import PreviewToolbar from "./PreviewToolbar";
import { parseMarkdown } from "@/lib/markdownParser";

interface DocumentPreviewProps {
  content: string;
  fileName?: string;
  fileSize?: number;
}

export default function DocumentPreview({ content, fileName, fileSize }: DocumentPreviewProps) {
  const [zoom, setZoom] = useState(100);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const parsed = useMemo(() => parseMarkdown(content), [content]);

  // Highlight search matches
  const highlightedHtml = useMemo(() => {
    if (!searchQuery) return parsed.html;
    const escaped = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return parsed.html.replace(regex, '<mark class="bg-accent/30 px-0.5 rounded">$1</mark>');
  }, [parsed.html, searchQuery]);

  // Simple pagination: split by headers
  const pages = useMemo(() => {
    const sections = content.split(/(?=^#{1,3}\s)/m).filter(Boolean);
    return sections.length > 0 ? sections : [content];
  }, [content]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
  }, []);

  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-text-tertiary">
        <FileText className="w-12 h-12 mb-4 opacity-50" />
        <p>暂无内容可预览</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface rounded-2xl border border-border overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent" />
          <span className="font-medium text-sm">{parsed.title}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-tertiary">
          <span>{parsed.wordCount} 字</span>
          <span>{parsed.lineCount} 行</span>
          {fileSize && <span>{formatFileSize(fileSize)}</span>}
        </div>
      </div>

      {/* Toolbar */}
      <PreviewToolbar
        zoom={zoom}
        onZoomChange={setZoom}
        onSearch={handleSearch}
        currentPage={currentPage}
        totalPages={pages.length}
        onPageChange={setCurrentPage}
        format="markdown"
        onFormatChange={() => {}}
      />

      {/* Content */}
      <motion.div
        className="flex-1 overflow-auto p-6"
        style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
      >
        <div 
          className="prose prose-sm max-w-none prose-headings:text-text-primary prose-p:text-text-secondary prose-strong:text-text-primary prose-blockquote:border-l-accent prose-blockquote:bg-accent/5 prose-code:bg-surface-subtle"
          dangerouslySetInnerHTML={{ __html: highlightedHtml }}
        />
      </motion.div>

      {/* Status Bar */}
      <div className="px-4 py-2 border-t border-border text-xs text-text-tertiary flex items-center justify-between">
        <span>UTF-8</span>
        {searchQuery && (
          <span className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            搜索: "{searchQuery}"
          </span>
        )}
      </div>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
```

---

### Task 9: Download Modal Component

**Files:**
- Create: `web-dashboard/src/components/DownloadModal.tsx`

- [ ] **Step 1: Create download modal**

```tsx
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, X, FileText, Image, FileJson, Archive, Check } from "lucide-react";
import { downloadFile, downloadZip, sanitizeFilename } from "@/lib/fileDownloader";

interface DownloadOption {
  id: string;
  label: string;
  icon: React.ElementType;
  extension: string;
  mimeType: string;
  content: string;
}

interface DownloadModalProps {
  isOpen: boolean;
  onClose: () => void;
  podcastName: string;
  episodeTitle: string;
  transcriptContent: string;
  noteContent: string;
  jsonContent: string;
  imageUrls?: string[];
}

export default function DownloadModal({
  isOpen,
  onClose,
  podcastName,
  episodeTitle,
  transcriptContent,
  noteContent,
  jsonContent,
  imageUrls = [],
}: DownloadModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set(['transcript_txt', 'note_md']));
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);

  const baseName = sanitizeFilename(`${podcastName}_${episodeTitle}`);

  const options: DownloadOption[] = [
    {
      id: 'transcript_txt',
      label: '转录文本 (TXT)',
      icon: FileText,
      extension: 'txt',
      mimeType: 'text/plain;charset=utf-8',
      content: transcriptContent,
    },
    {
      id: 'note_md',
      label: '笔记 (Markdown)',
      icon: FileText,
      extension: 'md',
      mimeType: 'text/markdown;charset=utf-8',
      content: noteContent,
    },
    {
      id: 'structured_json',
      label: '结构化数据 (JSON)',
      icon: FileJson,
      extension: 'json',
      mimeType: 'application/json;charset=utf-8',
      content: jsonContent,
    },
  ];

  const toggleSelection = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const handleDownload = async () => {
    if (selected.size === 0) return;
    
    setIsDownloading(true);
    setProgress(0);

    const files = options
      .filter(opt => selected.has(opt.id))
      .map(opt => ({
        name: `${baseName}_${opt.id.split('_')[0]}.${opt.extension}`,
        content: opt.content,
        type: opt.mimeType,
      }));

    // Add images if selected
    if (selected.has('images') && imageUrls.length > 0) {
      // Fetch images and add to files
      for (let i = 0; i < imageUrls.length; i++) {
        const url = imageUrls[i];
        try {
          const response = await fetch(url);
          const blob = await response.blob();
          files.push({
            name: `${baseName}_image_${i + 1}.png`,
            content: blob,
            type: 'image/png',
          });
          setProgress(Math.round(((i + 1) / imageUrls.length) * 100));
        } catch (e) {
          console.error('Failed to fetch image:', e);
        }
      }
    }

    if (files.length === 1) {
      downloadFile(files[0]);
    } else {
      await downloadZip(files, `${baseName}_all.zip`);
    }

    setIsDownloading(false);
    setProgress(100);
    setTimeout(() => onClose(), 500);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-surface rounded-2xl border border-border shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Download className="w-5 h-5 text-accent" />
                下载选项
              </h2>
              <button onClick={onClose} className="p-1 rounded-lg hover:bg-surface-subtle">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Options */}
            <div className="p-6 space-y-3">
              {options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => toggleSelection(opt.id)}
                  className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    selected.has(opt.id)
                      ? 'border-accent bg-accent/5'
                      : 'border-border hover:border-text-tertiary'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    selected.has(opt.id) ? 'bg-accent border-accent' : 'border-text-tertiary'
                  }`}>
                    {selected.has(opt.id) && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <opt.icon className="w-5 h-5 text-text-secondary" />
                  <span className="flex-1 text-left font-medium">{opt.label}</span>
                </button>
              ))}

              {/* Images option */}
              {imageUrls.length > 0 && (
                <button
                  onClick={() => toggleSelection('images')}
                  className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    selected.has('images')
                      ? 'border-accent bg-accent/5'
                      : 'border-border hover:border-text-tertiary'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    selected.has('images') ? 'bg-accent border-accent' : 'border-text-tertiary'
                  }`}>
                    {selected.has('images') && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <Image className="w-5 h-5 text-text-secondary" />
                  <span className="flex-1 text-left font-medium">
                    图片 ({imageUrls.length} 张)
                  </span>
                </button>
              )}

              {/* File name */}
              <div className="mt-4">
                <label className="text-xs text-text-tertiary mb-1 block">文件名</label>
                <input
                  type="text"
                  value={baseName}
                  readOnly
                  className="w-full px-3 py-2 bg-surface-subtle border border-border rounded-lg text-sm text-text-tertiary"
                />
              </div>

              {/* Progress */}
              {isDownloading && (
                <div className="mt-4">
                  <div className="h-2 bg-surface-subtle rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-accent rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-text-tertiary mt-1 text-center">{progress}%</p>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleDownload}
                disabled={selected.size === 0 || isDownloading}
                className="px-6 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Archive className="w-4 h-4" />
                {selected.size <= 1 ? '下载' : '打包下载'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

---

### Task 10: Proofread Panel Component

**Files:**
- Create: `web-dashboard/src/components/ProofreadPanel.tsx`

- [ ] **Step 1: Create proofread panel**

```tsx
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Check, X, Loader2, Sparkles } from "lucide-react";

interface ProofreadIssue {
  id: string;
  line: number;
  original: string;
  suggestion: string;
  type: string;
  context: string;
  accepted: boolean | null;
}

interface ProofreadPanelProps {
  issues: ProofreadIssue[];
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onApplyAll: () => void;
  onIgnoreAll: () => void;
  isLoading: boolean;
}

export default function ProofreadPanel({
  issues,
  onAccept,
  onReject,
  onApplyAll,
  onIgnoreAll,
  isLoading,
}: ProofreadPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const pendingCount = issues.filter(i => i.accepted === null).length;
  const acceptedCount = issues.filter(i => i.accepted === true).length;
  const rejectedCount = issues.filter(i => i.accepted === false).length;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-tertiary">
        <Loader2 className="w-8 h-8 animate-spin mb-3" />
        <p className="text-sm">正在校对文档...</p>
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-tertiary">
        <Sparkles className="w-8 h-8 mb-3 text-success" />
        <p className="text-sm">未发现明显错误</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Stats */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-warning" />
          <span className="font-medium text-sm">发现 {issues.length} 个问题</span>
        </div>
        <div className="flex gap-3 text-xs text-text-tertiary">
          <span className="text-warning">待处理: {pendingCount}</span>
          <span className="text-success">已接受: {acceptedCount}</span>
          <span className="text-text-tertiary">已忽略: {rejectedCount}</span>
        </div>
      </div>

      {/* Issue List */}
      <div className="flex-1 overflow-auto">
        <AnimatePresence>
          {issues.map((issue) => (
            <motion.div
              key={issue.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className={`border-b border-border ${
                issue.accepted === true ? 'bg-success/5' :
                issue.accepted === false ? 'bg-surface-subtle/50 opacity-50' : ''
              }`}
            >
              <button
                onClick={() => setExpandedId(expandedId === issue.id ? null : issue.id)}
                className="w-full px-4 py-3 text-left hover:bg-surface-subtle/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                    issue.type === 'grammar' ? 'bg-warning/10 text-warning' :
                    issue.type === 'spelling' ? 'bg-error/10 text-error' :
                    'bg-info/10 text-info'
                  }`}>
                    {issue.type === 'grammar' ? '语法' :
                     issue.type === 'spelling' ? '拼写' : '标点'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      <span className="line-through text-text-tertiary">{issue.original}</span>
                      {' → '}
                      <span className="text-success font-medium">{issue.suggestion}</span>
                    </p>
                    <p className="text-xs text-text-tertiary mt-1 truncate">
                      第 {issue.line} 行 · {issue.context}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                {issue.accepted === null && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); onAccept(issue.id); }}
                      className="flex items-center gap-1 px-3 py-1 bg-success/10 text-success rounded-lg text-xs font-medium hover:bg-success/20 transition-colors"
                    >
                      <Check className="w-3 h-3" />
                      接受
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onReject(issue.id); }}
                      className="flex items-center gap-1 px-3 py-1 bg-surface-subtle text-text-tertiary rounded-lg text-xs font-medium hover:bg-surface-subtle/80 transition-colors"
                    >
                      <X className="w-3 h-3" />
                      忽略
                    </button>
                  </div>
                )}
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Bulk Actions */}
      {pendingCount > 0 && (
        <div className="px-4 py-3 border-t border-border flex gap-2">
          <button
            onClick={onApplyAll}
            className="flex-1 py-2 bg-success/10 text-success rounded-lg text-xs font-medium hover:bg-success/20 transition-colors"
          >
            全部接受 ({pendingCount})
          </button>
          <button
            onClick={onIgnoreAll}
            className="flex-1 py-2 bg-surface-subtle text-text-tertiary rounded-lg text-xs font-medium hover:bg-surface-subtle/80 transition-colors"
          >
            全部忽略
          </button>
        </div>
      )}
    </div>
  );
}
```

---

### Task 11: Error Toast Component

**Files:**
- Create: `web-dashboard/src/components/ErrorToast.tsx`

- [ ] **Step 1: Create error toast**

```tsx
"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, X } from "lucide-react";

interface ErrorToastProps {
  message: string;
  isVisible: boolean;
  onClose: () => void;
  type?: 'error' | 'warning' | 'info';
}

export default function ErrorToast({ message, isVisible, onClose, type = 'error' }: ErrorToastProps) {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(onClose, 5000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  const colors = {
    error: 'bg-error/10 border-error/20 text-error',
    warning: 'bg-warning/10 border-warning/20 text-warning',
    info: 'bg-info/10 border-info/20 text-info',
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, x: '-50%' }}
          animate={{ opacity: 1, y: 0, x: '-50%' }}
          exit={{ opacity: 0, y: -20, x: '-50%' }}
          className={`fixed top-4 left-1/2 z-50 px-4 py-3 rounded-xl border ${colors[type]} shadow-lg flex items-center gap-3 max-w-md`}
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm font-medium">{message}</p>
          <button onClick={onClose} className="p-1 hover:bg-black/5 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

---

### Task 12: API Routes

**Files:**
- Create: `web-dashboard/src/app/api/proofread/route.ts`
- Create: `web-dashboard/src/app/api/download/route.ts`

- [ ] **Step 1: Create proofread API route**

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text } = await request.json();
    
    if (!text || typeof text !== 'string') {
      return NextResponse.json(
        { error: 'Text is required' },
        { status: 400 }
      );
    }

    // Call Python backend for proofreading
    // For now, return mock response
    const mockIssues = [
      {
        id: '1',
        line: 12,
        original: '快速的',
        suggestion: '快速地',
        type: 'grammar',
        context: '快速的成长需要耐心',
      },
    ];

    return NextResponse.json({ issues: mockIssues });
  } catch (error) {
    return NextResponse.json(
      { error: 'Proofreading failed', details: String(error) },
      { status: 500 }
    );
  }
}
```

- [ ] **Step 2: Create download API route**

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { fileName, content, format } = await request.json();
    
    if (!fileName || !content) {
      return NextResponse.json(
        { error: 'File name and content are required' },
        { status: 400 }
      );
    }

    // Set appropriate content type
    const mimeTypes: Record<string, string> = {
      txt: 'text/plain; charset=utf-8',
      md: 'text/markdown; charset=utf-8',
      json: 'application/json; charset=utf-8',
    };

    const headers = new Headers();
    headers.set('Content-Type', mimeTypes[format] || 'text/plain');
    headers.set('Content-Disposition', `attachment; filename="${fileName}"`);

    return new NextResponse(content, { headers });
  } catch (error) {
    return NextResponse.json(
      { error: 'Download failed', details: String(error) },
      { status: 500 }
    );
  }
}
```

---

### Task 13: Update Main Page Integration

**Files:**
- Modify: `web-dashboard/src/app/page.tsx`

- [ ] **Step 1: Add preview/download tabs to task detail**

Add state and integrate components:

```tsx
// Add to imports
import DocumentPreview from "@/components/DocumentPreview";
import DownloadModal from "@/components/DownloadModal";
import ProofreadPanel from "@/components/ProofreadPanel";
import ErrorToast from "@/components/ErrorToast";

// Add state
const [previewTab, setPreviewTab] = useState<"preview" | "proofread" | "download">("preview");
const [isDownloadOpen, setIsDownloadOpen] = useState(false);
const [proofreadIssues, setProofreadIssues] = useState<ProofreadIssue[]>([]);
const [isProofreading, setIsProofreading] = useState(false);
const [error, setError] = useState<string | null>(null);

// Add to task detail view
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
  <div className="lg:col-span-2">
    <DocumentPreview content={transcriptContent} />
  </div>
  <div className="lg:col-span-1">
    <ProofreadPanel 
      issues={proofreadIssues}
      onAccept={(id) => /* ... */}
      onReject={(id) => /* ... */}
      isLoading={isProofreading}
    />
  </div>
</div>
```

---

### Task 14: Tailwind Typography Plugin

**Files:**
- Modify: `web-dashboard/src/app/globals.css`

- [ ] **Step 1: Add prose styles for Markdown preview**

```css
@layer components {
  .prose {
    @apply text-text-secondary;
  }
  .prose h1 {
    @apply text-2xl font-bold text-text-primary mb-4 mt-6;
  }
  .prose h2 {
    @apply text-xl font-bold text-text-primary mb-3 mt-5;
  }
  .prose h3 {
    @apply text-lg font-semibold text-text-primary mb-2 mt-4;
  }
  .prose p {
    @apply mb-4 leading-relaxed;
  }
  .prose ul {
    @apply list-disc pl-5 mb-4;
  }
  .prose ol {
    @apply list-decimal pl-5 mb-4;
  }
  .prose blockquote {
    @apply border-l-4 border-accent pl-4 py-2 my-4 bg-accent/5 rounded-r-lg;
  }
  .prose code {
    @apply bg-surface-subtle px-1.5 py-0.5 rounded text-sm font-mono;
  }
  .prose pre {
    @apply bg-surface-subtle p-4 rounded-xl overflow-x-auto mb-4;
  }
  .prose pre code {
    @apply bg-transparent p-0;
  }
  .prose hr {
    @apply border-border my-6;
  }
  .prose a {
    @apply text-accent hover:underline;
  }
  .prose strong {
    @apply font-bold text-text-primary;
  }
  .prose em {
    @apply italic;
  }
}
```

---

### Task 15: Integration Testing

- [ ] **Step 1: Test full preview flow**

1. Open web dashboard
2. Select a completed task
3. Click "Preview" tab
4. Verify Markdown renders correctly
5. Test zoom controls
6. Test search highlight

- [ ] **Step 2: Test download flow**

1. Click "Download" button
2. Select multiple formats
3. Click "Download All"
4. Verify ZIP contains all selected files
5. Verify file names are sanitized

- [ ] **Step 3: Test proofreading flow**

1. Click "Proofread" tab
2. Wait for LLM analysis
3. Verify issues are displayed
4. Accept some, reject others
5. Verify "Apply All" works
6. Download corrected document

- [ ] **Step 4: Test error handling**

1. Try previewing empty file → show friendly message
2. Disconnect network during download → show retry option
3. Upload corrupted file → show validation error

---

## 4. Summary

This implementation plan covers:

1. **Backend enhancements**: Export methods (`to_txt`, `to_json`), document validator, proofreading engine
2. **Frontend components**: Preview panel, download modal, proofread sidebar, error toast
3. **Utilities**: Markdown parser, file downloader with ZIP support
4. **API routes**: Proofreading endpoint, file download endpoint
5. **Integration**: All components wired into the main dashboard

**Estimated effort**: 15-20 tasks, each 2-5 minutes. Total ~2-3 hours.

**Dependencies to install**: `marked`, `jszip`, `@types/marked`

**Key design decisions**:
- Client-side Markdown parsing for instant preview
- Client-side ZIP generation for batch downloads
- Non-blocking proofreading that doesn't prevent download
- Graceful fallbacks at every error point
