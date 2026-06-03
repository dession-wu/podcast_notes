# Dashboard Design & Implementation Plan

## 1. Design Language Analysis (from Reference HTML)

### Visual Identity
| Element | Specification |
|---------|--------------|
| Background | `#050507` deep black |
| Primary accent | White (`#ffffff`) for CTAs |
| Text primary | `#f0f2fa` off-white |
| Text secondary | `#9ca3af` gray-400 |
| Text muted | `#4b5563` gray-600 |
| Surface glass | `#0c0c0e` at 85% opacity |
| Border | `#1f1f22` (gray-900 equivalent) |
| Input bg | `#141416` |
| Border radius (cards) | `24px` (rounded-3xl) |
| Border radius (buttons) | `9999px` (full/pill) |
| Border radius (inputs) | `16px` (rounded-xl) |
| Font display | Monospace for labels/status |
| Font body | Sans-serif (Noto Sans SC) |
| Label style | `10px uppercase tracking-widest` |

### Interaction Patterns
- Buttons: `active:scale-[0.98]` on press
- Hover: `bg-white/5 → bg-white/10` transition
- Focus: `border-gray-700` on inputs
- Cards: `backdrop-blur-md` glass effect

### Background Animation
- Canvas-based pixel wave (sine wave + probability density)
- Config: density 2.5, dotSize 1.2, waveHeight 180, speed 0.015

---

## 2. Dashboard Architecture

### Page Structure
```
Dashboard Layout (keeps wave background)
├── Sidebar (collapsible on mobile)
│   ├── Logo: PODCAST NOTES
│   ├── Navigation Items:
│   │   ├── 🔍 播客搜索 (Podcast Search)
│   │   ├── 📥 下载管理 (Downloads)
│   │   ├── 📝 转录文本 (Transcripts)
│   │   ├── ✨ 内容提炼 (Content)
│   │   ├── 🎨 图片生成 (Images)
│   │   ├── 📤 发布管理 (Publish)
│   │   └── ⚙️ 系统设置 (Settings)
│   └── User Profile (bottom)
│
├── Main Content Area
│   ├── Header (breadcrumb + status)
│   └── Page Content (route-dependent)
│
└── Background: WaveCanvas (persistent)
```

### Route Structure
| Route | Content |
|-------|---------|
| `/dashboard` | Overview / Stats cards |
| `/dashboard/search` | Podcast search + results |
| `/dashboard/downloads` | Download queue + progress |
| `/dashboard/transcripts` | Transcript list + preview |
| `/dashboard/content` | Content processing + editor |
| `/dashboard/images` | Image gallery + generation |
| `/dashboard/publish` | XHS publish queue |
| `/dashboard/settings` | Config + API keys |

---

## 3. Component Inventory

### Layout Components
| Component | File | Description |
|-----------|------|-------------|
| `DashboardLayout` | `app/dashboard/layout.tsx` | Sidebar + main area wrapper |
| `Sidebar` | `components/Sidebar.tsx` | Navigation with active states |
| `SidebarItem` | `components/SidebarItem.tsx` | Individual nav item with icon |
| `TopBar` | `components/TopBar.tsx` | Breadcrumb + status indicators |
| `MobileNav` | `components/MobileNav.tsx` | Bottom sheet nav for mobile |

### Page Components
| Component | File | Description |
|-----------|------|-------------|
| `SearchPage` | `app/dashboard/search/page.tsx` | Podcast search interface |
| `DownloadPage` | `app/dashboard/downloads/page.tsx` | Download management |
| `TranscriptPage` | `app/dashboard/transcripts/page.tsx` | Transcript list + viewer |
| `ContentPage` | `app/dashboard/content/page.tsx` | AI content processing |
| `ImagePage` | `app/dashboard/images/page.tsx` | Image gallery |
| `PublishPage` | `app/dashboard/publish/page.tsx` | XHS publish queue |
| `SettingsPage` | `app/dashboard/settings/page.tsx` | Configuration |

### Shared Components
| Component | File | Description |
|-----------|------|-------------|
| `GlassCard` | `components/GlassCard.tsx` | Reusable glass panel |
| `StatusBadge` | `components/StatusBadge.tsx` | Status indicator (processing/done/error) |
| `ProgressBar` | `components/ProgressBar.tsx` | Animated progress |
| `DataTable` | `components/DataTable.tsx` | Sortable/filterable table |
| `EmptyState` | `components/EmptyState.tsx` | Empty state illustration |
| `Toast` | `components/Toast.tsx` | Notification system |

---

## 4. Implementation Tasks

### Task 1: Create Dashboard Layout
**Files:**
- `app/dashboard/layout.tsx` — Root layout with sidebar + wave bg
- `components/Sidebar.tsx` — Navigation sidebar
- `components/SidebarItem.tsx` — Nav item component
- `components/TopBar.tsx` — Header bar

**Design specs:**
- Sidebar width: `240px` desktop, `0px` collapsed, full-screen overlay mobile
- Glass effect: `bg-[#0c0c0e]/90 backdrop-blur-xl border-r border-gray-900`
- Active item: `bg-white/5 border-l-2 border-white`
- Inactive item: `text-gray-500 hover:text-gray-300 hover:bg-white/3`

### Task 2: Create Dashboard Home (Overview)
**File:** `app/dashboard/page.tsx`

**Content:**
- 4 stat cards (total podcasts, transcripts, images, published)
- Recent activity feed
- Quick action buttons

**Card design:**
```
bg-[#0c0c0e]/70 border border-gray-900 rounded-3xl p-6 backdrop-blur-md
```

### Task 3: Create Podcast Search Page
**File:** `app/dashboard/search/page.tsx`

**Content:**
- Search input with glass styling
- Results grid (podcast cards)
- Episode list expansion
- "Add to download" action

**API integration:**
```typescript
// POST /api/search
const results = await fetch('/api/search', {
  method: 'POST',
  body: JSON.stringify({ query: '知行小酒馆' })
});
```

### Task 4: Create Download Management Page
**File:** `app/dashboard/downloads/page.tsx`

**Content:**
- Download queue table
- Progress bars per item
- Status badges (queued/downloading/completed/error)
- Retry/cancel actions

### Task 5: Create Transcript Viewer Page
**File:** `app/dashboard/transcripts/page.tsx`

**Content:**
- Transcript list with metadata
- Markdown preview panel
- Segment timeline
- Export actions (TXT/JSON/SRT)

### Task 6: Create Content Processing Page
**File:** `app/dashboard/content/page.tsx`

**Content:**
- Transcript selector
- AI processing controls
- Xiaohongshu note preview
- Edit + regenerate actions

### Task 7: Create Image Gallery Page
**File:** `app/dashboard/images/page.tsx`

**Content:**
- Image grid (masonry layout)
- Preview modal
- Download PNG action
- Regenerate action

### Task 8: Create Publish Queue Page
**File:** `app/dashboard/publish/page.tsx`

**Content:**
- Publish queue list
- Status tracking
- Preview before publish
- XHS account connection

### Task 9: Create Settings Page
**File:** `app/dashboard/settings/page.tsx`

**Content:**
- API key inputs (LLM, STT, PodcastIndex)
- Provider selection dropdowns
- Theme toggle
- Log level selector

### Task 10: Update globals.css
Add dashboard-specific utilities:
- `.dashboard-grid` — CSS grid for cards
- `.status-dot` — Animated status indicator
- `.progress-track` — Progress bar track
- `.progress-fill` — Progress bar fill

### Task 11: Build & Verify
- `npm run build` — Check TypeScript
- Verify all routes compile
- Test responsive breakpoints
- Check accessibility (WCAG 2.1)

---

## 5. Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `≥1280px` (xl) | Full sidebar + 4-col grid |
| `≥1024px` (lg) | Full sidebar + 3-col grid |
| `≥768px` (md) | Collapsible sidebar + 2-col grid |
| `<768px` (sm) | Bottom nav + 1-col stack |

---

## 6. Accessibility (WCAG 2.1)

- All interactive elements have `focus-visible` rings
- Color contrast ≥ 4.5:1 for text
- ARIA labels on icon buttons
- Keyboard navigation for sidebar
- Reduced motion support: `@media (prefers-reduced-motion: reduce)`
- Skip link for main content

---

## 7. API Routes Needed

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/search` | POST | Search podcasts |
| `/api/download` | POST | Queue audio download |
| `/api/transcribe` | POST | Start transcription |
| `/api/process` | POST | AI content processing |
| `/api/generate-image` | POST | Generate XHS images |
| `/api/publish` | POST | Queue XHS publish |
| `/api/settings` | GET/PUT | Read/update config |

---

## 8. Summary

This plan creates a complete dashboard that:
1. **Maintains design consistency** — Uses the same glassmorphism, dark theme, and wave background
2. **Connects to backend** — Every page has a corresponding API route
3. **Is fully responsive** — Desktop sidebar + mobile bottom nav
4. **Follows WCAG 2.1** — Accessible keyboard navigation and contrast
5. **Uses existing components** — Reuses WaveCanvas, GlassCard patterns

**Estimated effort:** 11 tasks, ~4-5 hours
**Key files to create:** ~20 new files
**Key files to modify:** `globals.css`, `layout.tsx`
