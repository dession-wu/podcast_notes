# 搜索下载功能增强 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强搜索结果页面的下载功能，添加下载进度指示、完成提示、失败重试、批量下载等用户体验优化。

**Architecture:**
- 后端改造下载 API 为异步任务模式，支持进度上报、断点续传元数据记录
- 前端改造下载状态管理，从简单 loading 升级为完整状态机（pending/progress/completed/failed）
- 新增下载历史记录组件，展示最近下载任务

**Tech Stack:** FastAPI, Next.js 16, React 19, TypeScript, Tailwind CSS, Framer Motion

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/routers/download.py` | 修改 | 下载 API：异步任务 + 进度上报 + 断点续传元数据 |
| `backend/core/audio_downloader.py` | 修改 | 下载器：流式下载 + 进度回调 |
| `web-dashboard/src/lib/api.ts` | 修改 | 前端 API：更新下载类型，添加批量下载接口 |
| `web-dashboard/src/app/dashboard/search/page.tsx` | 修改 | 搜索页面：增强下载按钮状态展示 |
| `web-dashboard/src/components/DownloadManager.tsx` | 新建 | 下载管理组件：进度条、完成提示、失败重试 |
| `web-dashboard/src/components/DownloadHistory.tsx` | 新建 | 下载历史侧边栏 |

---

## 现有能力分析

### 后端已有能力
- `download.py` 路由：同步下载，无进度上报
- `AudioDownloader.download_episode()`：流式下载，但无进度回调
- `AudioDownloader.download_from_rss()`：支持按索引选择单集
- 内存中的 jobs 字典存储任务状态

### 前端已有能力
- 搜索页面：每个播客卡片有下载按钮，显示 loading 动画
- 简单轮询：每 2 秒查询下载状态
- 成功/失败提示：顶部 toast 通知

### 当前问题
1. 下载是同步阻塞的，大文件下载时前端长时间无响应
2. 无进度指示，用户不知道下载了多少
3. 失败时无重试按钮，需重新点击下载
4. 无批量下载能力
5. 无下载历史记录

---

## Task 1: 后端 — 改造下载为异步任务 + 进度上报

### 1.1 修改 `audio_downloader.py` 添加进度回调

**文件:** `backend/core/audio_downloader.py`

**步骤:**

- [ ] **Step 1: 修改 `download_episode` 方法支持进度回调**

找到 `download_episode` 方法，修改其签名和流式下载逻辑：

```python
def download_episode(
    self,
    episode: PodcastEpisode,
    force: bool = False,
    progress_callback: callable | None = None,
) -> Path:
```

在流式下载的循环中添加进度回调：

```python
# 流式下载
chunk_size = 8192
for chunk in response.iter_content(chunk_size=chunk_size):
    if chunk:
        f.write(chunk)
        downloaded += len(chunk)
        
        if progress_callback and total_size > 0:
            progress = min(100.0, (downloaded / total_size) * 100)
            progress_callback(progress, downloaded, total_size)
```

### 1.2 修改 `download.py` 路由为异步任务模式

**文件:** `backend/routers/download.py`

- [ ] **Step 2: 添加后台任务执行函数**

在路由文件顶部添加：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 线程池用于执行同步下载操作
download_executor = ThreadPoolExecutor(max_workers=3)
```

- [ ] **Step 3: 添加进度更新辅助函数**

```python
def update_progress(task_id: str, progress: float, downloaded: int, total: int):
    """更新下载进度."""
    if task_id in jobs:
        jobs[task_id]["progress"] = progress
        jobs[task_id]["downloaded_bytes"] = downloaded
        jobs[task_id]["total_bytes"] = total
```

- [ ] **Step 4: 修改 `start_download` 为异步启动**

将同步下载改为在线程池中执行：

```python
@router.post("/", response_model=DownloadResponse)
async def start_download(request: DownloadRequest):
    task_id = str(uuid.uuid4())
    
    jobs[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "result": None,
        "error": None,
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
        logger.error("Download failed", error=str(e), task_id=task_id)
        jobs[task_id]["status"] = "failed"
        jobs[task_id]["error"] = str(e)
```

注意：需要修改 `download_from_rss` 以传递 `progress_callback` 到 `download_episode`。

- [ ] **Step 5: 修改 `DownloadStatusResponse` 添加进度字段**

```python
class DownloadStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float | None = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    result: dict | None = None
    error: str | None = None
```

- [ ] **Step 6: 修改 `get_download_status` 返回新字段**

```python
@router.get("/{task_id}", response_model=DownloadStatusResponse)
async def get_download_status(task_id: str):
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
    )
```

- [ ] **Step 7: 添加重试接口**

```python
class RetryRequest(BaseModel):
    task_id: str

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
    
    # 重新启动下载
    retry_request = DownloadRequest(
        rss_url=job["rss_url"],
        episode_index=job["episode_index"],
    )
    asyncio.create_task(_do_download(request.task_id, retry_request))
    
    return DownloadResponse(task_id=request.task_id, status="processing")
```

- [ ] **Step 8: 添加批量下载接口**

```python
class BatchDownloadRequest(BaseModel):
    rss_url: str
    episode_indices: list[int]

class BatchDownloadResponse(BaseModel):
    batch_id: str
    task_ids: list[str]
    total: int

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
```

- [ ] **Step 9: 添加下载历史接口**

```python
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
        })
    
    return {"history": history}
```

---

## Task 2: 前端 — 更新 API 类型

**文件:** `web-dashboard/src/lib/api.ts`

- [ ] **Step 10: 更新下载相关类型**

修改 `DownloadStatusResponse`：

```typescript
export interface DownloadStatusResponse {
  task_id: string;
  status: string;
  progress?: number;
  downloaded_bytes?: number;
  total_bytes?: number;
  result?: {
    file_path: string;
    file_name: string;
    file_size_mb: number;
    episode_title: string;
    podcast_name: string;
    duration_seconds?: number;
  };
  error?: string;
}
```

添加批量下载类型和函数：

```typescript
export interface BatchDownloadRequest {
  rss_url: string;
  episode_indices: number[];
}

export interface BatchDownloadResponse {
  batch_id: string;
  task_ids: string[];
  total: number;
}

export async function batchDownload(
  request: BatchDownloadRequest
): Promise<BatchDownloadResponse> {
  return fetchApi<BatchDownloadResponse>("/api/download/batch", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function retryDownload(taskId: string): Promise<DownloadResponse> {
  return fetchApi<DownloadResponse>("/api/download/retry", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}

export interface DownloadHistoryItem {
  task_id: string;
  status: string;
  progress?: number;
  episode_title: string;
  podcast_name: string;
  file_size_mb?: number;
  created_at?: number;
  error?: string;
}

export async function getDownloadHistory(limit: number = 20): Promise<{ history: DownloadHistoryItem[] }> {
  return fetchApi<{ history: DownloadHistoryItem[] }>(`/api/download/history/list?limit=${limit}`);
}
```

---

## Task 3: 前端 — 创建下载管理组件

**文件:** `web-dashboard/src/components/DownloadManager.tsx` (新建)

- [ ] **Step 11: 创建下载管理组件**

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download,
  Loader2,
  CheckCircle2,
  XCircle,
  RotateCcw,
  FolderOpen,
  FileAudio,
  X,
} from "lucide-react";
import { getDownloadStatus, retryDownload, DownloadStatusResponse } from "@/lib/api";

interface DownloadTask {
  taskId: string;
  podcastTitle: string;
  episodeTitle?: string;
  status: string;
  progress: number;
  error?: string;
  result?: DownloadStatusResponse["result"];
}

interface DownloadManagerProps {
  tasks: DownloadTask[];
  onClose: () => void;
  onRetry: (taskId: string) => void;
  onRemove: (taskId: string) => void;
}

export default function DownloadManager({ tasks, onClose, onRetry, onRemove }: DownloadManagerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 300 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 300 }}
      className="fixed right-0 top-0 h-full w-96 bg-[#0a0a0a]/95 backdrop-blur-xl border-l border-white/[0.06] z-50 overflow-hidden flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Download className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-medium text-white">下载管理</h3>
          {tasks.length > 0 && (
            <span className="text-xs text-gray-500">({tasks.length})</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-500 hover:text-white transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {tasks.length === 0 ? (
          <div className="text-center py-12">
            <Download className="w-8 h-8 text-gray-700 mx-auto mb-3" />
            <p className="text-xs text-gray-600">暂无下载任务</p>
          </div>
        ) : (
          <AnimatePresence>
            {tasks.map((task) => (
              <motion.div
                key={task.taskId}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 100 }}
                className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center flex-shrink-0">
                    {task.status === "completed" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : task.status === "failed" ? (
                      <XCircle className="w-4 h-4 text-red-400" />
                    ) : (
                      <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white font-medium truncate">
                      {task.episodeTitle || "下载任务"}
                    </p>
                    <p className="text-[10px] text-gray-600 truncate">
                      {task.podcastTitle}
                    </p>
                    
                    {/* Progress bar */}
                    {task.status === "processing" && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                          <span>{task.progress.toFixed(1)}%</span>
                          <span>
                            {task.result?.file_size_mb 
                              ? `${(task.result.file_size_mb * task.progress / 100).toFixed(1)} / ${task.result.file_size_mb} MB`
                              : "下载中..."
                            }
                          </span>
                        </div>
                        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-emerald-500 rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${task.progress}%` }}
                            transition={{ duration: 0.3 }}
                          />
                        </div>
                      </div>
                    )}
                    
                    {/* Completed */}
                    {task.status === "completed" && task.result && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] text-emerald-400">
                          {task.result.file_size_mb} MB
                        </span>
                        <button
                          onClick={() => {
                            // Open file location - would need electron or similar for real implementation
                            alert(`文件位置: ${task.result?.file_path}`);
                          }}
                          className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-white transition"
                        >
                          <FolderOpen className="w-3 h-3" />
                          打开位置
                        </button>
                      </div>
                    )}
                    
                    {/* Failed */}
                    {task.status === "failed" && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] text-red-400 truncate">
                          {task.error || "下载失败"}
                        </span>
                        <button
                          onClick={() => onRetry(task.taskId)}
                          className="flex items-center gap-1 text-[10px] text-amber-400 hover:text-amber-300 transition"
                        >
                          <RotateCcw className="w-3 h-3" />
                          重试
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {/* Remove button */}
                  <button
                    onClick={() => onRemove(task.taskId)}
                    className="p-1 text-gray-600 hover:text-gray-400 transition flex-shrink-0"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  );
}
```

---

## Task 4: 前端 — 修改搜索页面集成下载管理

**文件:** `web-dashboard/src/app/dashboard/search/page.tsx`

- [ ] **Step 12: 导入 DownloadManager 并添加下载任务状态管理**

在现有导入中添加：
```typescript
import DownloadManager from "@/components/DownloadManager";
import { Download, History } from "lucide-react";
```

在组件 state 中添加：
```typescript
interface DownloadTaskState {
  taskId: string;
  podcastTitle: string;
  episodeTitle?: string;
  status: string;
  progress: number;
  error?: string;
  result?: any;
}

const [downloadTasks, setDownloadTasks] = useState<DownloadTaskState[]>([]);
const [showDownloadManager, setShowDownloadManager] = useState(false);
```

- [ ] **Step 13: 修改 `handleDownload` 使用新状态管理**

将现有的 `handleDownload` 替换为增强版本：

```typescript
const handleDownload = async (podcast: PodcastResult, episodeIndex: number = 0, episodeTitle?: string) => {
  if (!podcast.rss_url) {
    setDownloadError("该播客没有提供 RSS 链接，无法下载");
    return;
  }

  setDownloadError("");
  setDownloadSuccess(null);

  try {
    const response = await startDownload({
      rss_url: podcast.rss_url,
      episode_index: episodeIndex,
    });

    // 添加到任务列表
    const newTask: DownloadTaskState = {
      taskId: response.task_id,
      podcastTitle: podcast.title,
      episodeTitle: episodeTitle || "最新单集",
      status: "processing",
      progress: 0,
    };
    setDownloadTasks((prev) => [newTask, ...prev]);
    setShowDownloadManager(true);

    // 轮询进度
    const pollInterval = setInterval(async () => {
      try {
        const status = await getDownloadStatus(response.task_id);
        
        setDownloadTasks((prev) =>
          prev.map((task) =>
            task.taskId === response.task_id
              ? {
                  ...task,
                  status: status.status,
                  progress: status.progress || 0,
                  result: status.result,
                  error: status.error,
                }
              : task
          )
        );

        if (status.status === "completed") {
          clearInterval(pollInterval);
          setDownloadSuccess(`《${status.result?.episode_title || "未知单集"}》下载完成`);
          setTimeout(() => setDownloadSuccess(null), 5000);
        } else if (status.status === "failed") {
          clearInterval(pollInterval);
        }
      } catch (err) {
        clearInterval(pollInterval);
      }
    }, 1000);

  } catch (err) {
    setDownloadError(err instanceof Error ? err.message : "下载失败");
  }
};

const handleRetry = async (taskId: string) => {
  try {
    await retryDownload(taskId);
    
    // 更新任务状态为处理中
    setDownloadTasks((prev) =>
      prev.map((task) =>
        task.taskId === taskId
          ? { ...task, status: "processing", progress: 0, error: undefined }
          : task
      )
    );

    // 重新轮询
    const pollInterval = setInterval(async () => {
      try {
        const status = await getDownloadStatus(taskId);
        setDownloadTasks((prev) =>
          prev.map((task) =>
            task.taskId === taskId
              ? {
                  ...task,
                  status: status.status,
                  progress: status.progress || 0,
                  result: status.result,
                  error: status.error,
                }
              : task
          )
        );
        if (status.status === "completed" || status.status === "failed") {
          clearInterval(pollInterval);
        }
      } catch {
        clearInterval(pollInterval);
      }
    }, 1000);

  } catch (err) {
    console.error("Retry failed:", err);
  }
};

const handleRemoveTask = (taskId: string) => {
  setDownloadTasks((prev) => prev.filter((task) => task.taskId !== taskId));
};
```

- [ ] **Step 14: 添加下载管理器按钮和面板**

在搜索输入框区域（`</motion.div>` 闭合之前）添加下载管理器触发按钮：

```tsx
        {/* Download Manager Toggle */}
        {downloadTasks.length > 0 && (
          <button
            onClick={() => setShowDownloadManager(!showDownloadManager)}
            className="fixed right-6 top-6 z-40 flex items-center gap-2 px-4 py-2 bg-white/[0.05] border border-white/[0.08] rounded-xl text-xs text-gray-400 hover:bg-white/[0.08] transition"
          >
            <Download className="w-4 h-4" />
            <span>{downloadTasks.filter(t => t.status === "processing").length} 个下载中</span>
            {downloadTasks.some(t => t.status === "completed") && (
              <span className="w-2 h-2 bg-emerald-400 rounded-full" />
            )}
          </button>
        )}
```

在页面底部（`</div>` 闭合之前）添加 DownloadManager 组件：

```tsx
      <AnimatePresence>
        {showDownloadManager && (
          <DownloadManager
            tasks={downloadTasks}
            onClose={() => setShowDownloadManager(false)}
            onRetry={handleRetry}
            onRemove={handleRemoveTask}
          />
        )}
      </AnimatePresence>
```

- [ ] **Step 15: 修改 EpisodeList 中的下载调用**

EpisodeList 组件中的 `handleDownload` 需要改为调用父组件传入的下载函数。修改 EpisodeList 的 props：

```typescript
interface EpisodeListProps {
  rssUrl: string;
  podcastTitle: string;
  onClose: () => void;
  onDownload?: (episodeIndex: number, episodeTitle: string) => void;
}
```

在 EpisodeList 的 `handleDownload` 中：
```typescript
const handleDownload = async (episode: EpisodeItem) => {
  if (onDownload) {
    onDownload(episode.index, episode.title);
    return;
  }
  // 原有逻辑...
};
```

在 search/page.tsx 中传递 onDownload：
```tsx
<EpisodeList
  rssUrl={podcast.rss_url}
  podcastTitle={podcast.title}
  onClose={() => setExpandedPodcastId(null)}
  onDownload={(idx, title) => handleDownload(podcast, idx, title)}
/>
```

---

## Task 5: 构建和测试

- [ ] **Step 16: 运行前端构建**

```bash
cd d:\podcast_notes\web-dashboard
npm run build
```

- [ ] **Step 17: 验证后端路由**

```bash
cd d:\podcast_notes
python -m backend.main
```

测试下载 API：
```bash
python -c "
from backend.main import app
from fastapi.testclient import TestClient
c = TestClient(app)

# Start download
r = c.post('/api/download/', json={'rss_url': 'https://pythontest.com/testandcode_feed.xml', 'episode_index': 0})
print('Start:', r.status_code, r.json())
task_id = r.json()['task_id']

# Check status
import time
time.sleep(2)
r = c.get(f'/api/download/{task_id}')
print('Status:', r.status_code, r.json())
"
```

- [ ] **Step 18: 浏览器端验证**

1. 搜索播客，点击下载按钮
2. 确认下载管理器侧边栏弹出
3. 确认进度条实时更新
4. 等待下载完成，确认显示文件大小和"打开位置"按钮
5. 测试下载失败时的重试功能
6. 测试批量下载（通过 EpisodeList 选择多个单集）

---

## UI/UX 设计说明

### 下载管理器侧边栏

- 从右侧滑入，宽度 384px (w-96)
- 半透明背景 + 毛玻璃效果
- 显示所有下载任务的状态
- 每个任务卡片包含：状态图标、标题、播客名、进度条/结果/错误

### 任务状态展示

| 状态 | 图标 | 颜色 | 操作 |
|------|------|------|------|
| processing | Loader2 (旋转) | amber | 显示进度条 |
| completed | CheckCircle2 | emerald | 显示文件大小 + 打开位置 |
| failed | XCircle | red | 显示错误 + 重试按钮 |

### 进度条设计

- 高度 4px，圆角
- 背景色 gray-800
- 进度色 emerald-500
- 带动画过渡效果

---

## 数据流说明

### 单文件下载流程

```
用户点击下载按钮
  → 前端调用 POST /api/download/ (立即返回 task_id)
    → 后端创建 job，状态为 pending
    → 后端启动 asyncio 后台任务
      → 在线程池中执行同步下载
        → 下载过程中通过回调更新进度
    → 前端收到 task_id，添加到任务列表
    → 前端轮询 GET /api/download/{task_id} (每秒)
      → 实时更新进度条
      → 完成后显示结果
```

### 重试流程

```
用户点击重试按钮
  → 前端调用 POST /api/download/retry
    → 后端重置任务状态为 pending
    → 后端重新启动下载任务
    → 前端更新任务状态为 processing
    → 前端继续轮询进度
```

### 批量下载流程

```
用户在 EpisodeList 中选择多个单集
  → 前端调用 POST /api/download/batch
    → 后端创建多个任务，并行下载
    → 前端收到 batch_id 和 task_ids
    → 前端轮询所有任务状态
      → 显示总体进度
```
