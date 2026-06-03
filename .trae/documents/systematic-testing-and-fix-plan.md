# 功能模块系统性测试与修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全面测试项目所有功能模块，识别路由逻辑问题、功能重复、错误点，制定并实施修复。

**Architecture:** 基于代码审查结果，按优先级分阶段修复后端路由、前端页面、API 不匹配问题。

**Tech Stack:** FastAPI, React/Next.js, TypeScript, Python 3.11+

---

## Phase 1: 功能路由逻辑梳理（已完成代码审查）

### 后端路由清单

| Router | Prefix | Endpoints | 状态 |
|--------|--------|-----------|------|
| health | `/api/health` | GET `/` | ✅ |
| search | `/api/search` | POST `/` | ✅ |
| process | `/api/process` | POST `/` | ✅ |
| transcribe | `/api/transcribe` | POST `/`, GET `/{task_id}` | ✅ |
| download | `/api/download` | POST `/`, GET `/{task_id}`, POST `/retry`, POST `/batch`, GET `/history/list`, POST `/open-folder/{task_id}` | ✅ |
| images | `/api/images` | POST `/`, GET `/{task_id}` | ✅ |
| episodes | `/api/episodes` | POST `/` | ✅ |
| settings | `/api/settings` | GET `/download-path`, POST `/download-path`, POST `/download-path/reset`, POST `/download-path/validate` | ✅ |
| library | `/api/library` | GET `/files`, POST `/open-file` | ✅ |

### 前端页面清单

| 页面 | 路径 | 调用 API | 状态 |
|------|------|----------|------|
| Dashboard (概览) | `/dashboard` | `getHealthStatus()` | ✅ |
| Search (播客搜索) | `/dashboard/search` | `searchPodcasts()`, `startDownload()`, `getDownloadStatus()`, `retryDownload()` | ⚠️ 有错误 |
| Library (文件库) | `/dashboard/library` | `getLibraryFiles()`, `POST /api/library/open-file` | ✅ |
| Create (内容创作) | `/dashboard/create` | `processContent()`, `startImageGeneration()`, `getImageStatus()` | ✅ |
| Settings (系统设置) | `/dashboard/settings` | `getDownloadSettings()`, `updateDownloadSettings()`, `resetDownloadSettings()`, `validateDownloadPath()` | ✅ |

---

## Phase 2: 功能逻辑重复检测

### 已识别问题

| # | 问题 | 严重程度 | 说明 |
|---|------|----------|------|
| R1 | `DownloadManager.tsx` 组件未被使用 | 低 | Search 页面已移除 DownloadManager，但组件文件仍存在 |
| R2 | `openDownloadFolder` API 函数存在但无消费者 | 低 | 原 DownloadManager 使用，现 library 页面直接调用 `/api/library/open-file` |
| R3 | `getDownloadHistory` API 函数无消费者 | 低 | 原 Downloads 页面使用，现页面已删除 |
| R4 | `downloadAudio` API 函数无消费者 | 低 | 原 Search 页面使用，现改为 `startDownload` |
| R5 | `getTranscriptionStatus` API 函数无消费者 | 低 | Transcripts 页面已删除 |
| R6 | `startTranscription` API 函数无消费者 | 低 | Transcripts 页面已删除 |

---

## Phase 3: 功能错误排查（已识别问题）

### 🔴 P0 - 严重错误

| # | 问题 | 位置 | 影响 | 复现步骤 |
|---|------|------|------|----------|
| E1 | **Search 页面调用不存在的 API** | `search/page.tsx:22` | 下载功能完全不可用 | 点击搜索结果下载按钮 → 调用 `startDownload()` → 404 |

**详细分析：**
- `search/page.tsx` 导入并调用了 `startDownload()`
- 但 `api.ts` 中**不存在** `startDownload` 函数
- `api.ts` 中只有 `downloadAudio()`（旧 API）
- 后端 `download.py` 的入口是 `POST /`（`start_download`）
- **不匹配**：前端调用 `startDownload`，但 api.ts 没有导出这个函数

### 🟡 P1 - 重要错误

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| E2 | **Search 页面导入不存在的类型** | `search/page.tsx:18` | TypeScript 编译可能失败 |
| E3 | **Search 页面调用不存在的函数** | `search/page.tsx:24` | 重试功能不可用 |
| E4 | **ContentProcessor 使用不存在的类型** | `create/ContentProcessor.tsx:19` | TypeScript 类型错误 |
| E5 | **ImageGenerator 使用不存在的类型** | `create/ImageGenerator.tsx` | TypeScript 类型错误 |
| E6 | **前端 API 函数名与后端不匹配** | `api.ts` | 多处调用可能失败 |

### 🟢 P2 - 次要问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| E7 | **未使用的导入和函数** | `api.ts` | 代码冗余，维护困难 |
| E8 | **DownloadManager 组件孤立** | `components/DownloadManager.tsx` | 代码冗余 |
| E9 | **backend/config 目录缺少 __init__.py** | `backend/config/` | Python 导入可能失败 |

---

## Phase 4: 问题文档

### E1: Search 页面调用不存在的 API

**表现：** 点击播客搜索结果中的下载按钮，功能无响应或报错。

**复现步骤：**
1. 进入「播客搜索」页面
2. 输入关键词搜索
3. 点击任意搜索结果的下载按钮
4. 浏览器控制台报错：`startDownload is not defined` 或 404

**影响范围：** 播客下载核心功能完全不可用。

**根因：**
- 重构时 Search 页面改为调用 `startDownload()`
- 但 `api.ts` 中没有导出这个函数
- `api.ts` 中只有旧的 `downloadAudio()`
- 后端路由 `download.py` 使用的是 `start_download`（无 `startDownload` 别名）

**修复方案：** 在 `api.ts` 中添加 `startDownload` 函数，调用 `POST /api/download/`。

### E2: Search 页面导入不存在的类型 `DownloadTask`

**表现：** TypeScript 编译报错。

**根因：** `search/page.tsx` 从 `@/components/DownloadManager` 导入 `DownloadTask` 类型，但该组件可能未导出此类型。

**修复方案：** 在 `api.ts` 中定义并导出 `DownloadTask` 类型，Search 页面从 `api.ts` 导入。

### E3: Search 页面调用不存在的 `retryDownload`

**表现：** 下载重试功能不可用。

**根因：** `api.ts` 中没有 `retryDownload` 函数。

**修复方案：** 在 `api.ts` 中添加 `retryDownload` 函数，调用 `POST /api/download/retry`。

### E4/E5: ContentProcessor/ImageGenerator 类型不匹配

**表现：** TypeScript 编译报错。

**根因：**
- `ContentProcessor.tsx` 使用 `ProcessResponse["note"]` 类型
- `api.ts` 中 `ProcessResponse` 的 `note` 字段类型为 `XiaohongshuNote` 对象，不是简单字典
- `ImageGenerator.tsx` 使用 `ImageStatusResponse` 类型，但 `api.ts` 中该类型定义与组件使用方式可能不匹配

**修复方案：** 统一类型定义，确保前后端类型一致。

### E6: API 函数名与后端不匹配

**表现：** 多处调用可能失败。

**具体问题：**
| 前端调用 | 实际函数 | 后端路径 |
|----------|----------|----------|
| `startDownload()` | ❌ 不存在 | `POST /api/download/` |
| `retryDownload()` | ❌ 不存在 | `POST /api/download/retry` |
| `downloadAudio()` | ✅ 存在但无消费者 | `POST /api/download/` |
| `getDownloadHistory()` | ✅ 存在但无消费者 | `GET /api/download/history/list` |

**修复方案：** 统一命名，添加缺失函数，删除无用函数。

### E9: backend/config 缺少 __init__.py

**表现：** Python 导入 `backend.config.download_settings` 可能失败。

**修复方案：** 创建 `backend/config/__init__.py` 空文件。

---

## Phase 5: 修复方案与实施计划

### Task 1: 修复 api.ts - 添加缺失函数，统一命名

**Files:**
- Modify: `web-dashboard/src/lib/api.ts`

- [ ] **Step 1: 添加 `startDownload` 函数**

```typescript
export interface StartDownloadRequest {
  rss_url: string;
  episode_index?: number;
}

export interface StartDownloadResponse {
  task_id: string;
  status: string;
}

export async function startDownload(request: StartDownloadRequest): Promise<StartDownloadResponse> {
  return fetchApi<StartDownloadResponse>("/api/download/", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
```

- [ ] **Step 2: 添加 `retryDownload` 函数**

```typescript
export interface RetryDownloadRequest {
  task_id: string;
}

export async function retryDownload(taskId: string): Promise<DownloadResponse> {
  return fetchApi<DownloadResponse>("/api/download/retry", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}
```

- [ ] **Step 3: 添加 `DownloadTask` 类型导出**

```typescript
export interface DownloadTask {
  taskId: string;
  podcastTitle: string;
  episodeTitle: string;
  status: "processing" | "completed" | "failed";
  progress: number;
  result?: {
    file_path: string;
    file_name: string;
    file_size_mb: number;
    episode_title: string;
    podcast_name: string;
  };
  error?: string;
}
```

- [ ] **Step 4: 删除无用的旧函数**

删除 `downloadAudio()` 和 `getDownloadHistory()`（如果确认无消费者）。

### Task 2: 修复 Search 页面类型导入

**Files:**
- Modify: `web-dashboard/src/app/dashboard/search/page.tsx`

- [ ] **Step 1: 从 api.ts 导入类型**

```typescript
import {
  searchPodcasts,
  PodcastResult,
  startDownload,
  getDownloadStatus,
  retryDownload,
  DownloadTask,
} from "@/lib/api";
```

- [ ] **Step 2: 移除 DownloadManager 导入**

删除：`import { DownloadTask } from "@/components/DownloadManager";`

### Task 3: 修复 ContentProcessor 类型

**Files:**
- Modify: `web-dashboard/src/app/dashboard/create/ContentProcessor.tsx`

- [ ] **Step 1: 修复 note 类型**

```typescript
const [note, setNote] = useState<{ title: string; content: string; tags: string[] } | null>(null);
```

### Task 4: 创建 backend/config/__init__.py

**Files:**
- Create: `backend/config/__init__.py`

- [ ] **Step 1: 创建空文件**

```python
"""Backend configuration package."""
```

### Task 5: 清理无用代码

**Files:**
- Delete: `web-dashboard/src/components/DownloadManager.tsx`（如果确认无消费者）
- 或保留但标记为 deprecated

### Task 6: 构建与验证

- [ ] **Step 1: Frontend build**

Run: `cd web-dashboard && npm run build`
Expected: No errors

- [ ] **Step 2: Backend syntax check**

Run: `python -m py_compile backend/config/__init__.py`
Expected: Pass

- [ ] **Step 3: 验证后端启动**

Run: `python -c "from backend.main import app; print('OK')"`
Expected: OK

---

## 验证清单

- [ ] Search 页面下载按钮调用 `startDownload()` 成功
- [ ] Search 页面重试按钮调用 `retryDownload()` 成功
- [ ] Library 页面文件列表加载成功
- [ ] Library 页面「打开位置」功能正常
- [ ] Create 页面 AI 笔记生成成功
- [ ] Create 页面图片生成成功
- [ ] Settings 页面存储路径配置成功
- [ ] Dashboard 页面统计数字显示正常
- [ ] 前端构建无错误
- [ ] 后端启动无异常
