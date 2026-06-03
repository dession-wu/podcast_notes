# 下载功能用户体验全面审计与改进计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全面审计并改进播客下载功能的用户体验，确保下载流程可靠、透明、易用，包含实时进度显示、完善的错误处理、下载位置管理和文件访问功能。

**Architecture:** 基于现有 Next.js + FastAPI 架构，增强前端下载状态管理组件，完善后端下载任务追踪和错误分类，建立前后端一致的下载状态同步机制。

**Tech Stack:** Next.js 16 + React 19 + Tailwind CSS v4 + Framer Motion (前端), FastAPI + Python (后端)

---

## 文件结构

### 前端修改
- `web-dashboard/src/app/dashboard/search/page.tsx` — 搜索页面下载逻辑增强
- `web-dashboard/src/components/DownloadManager.tsx` — 下载管理器面板增强
- `web-dashboard/src/components/EpisodeList.tsx` — 单集列表下载交互增强
- `web-dashboard/src/lib/api.ts` — API 客户端（已修复路径，无需修改）
- `web-dashboard/src/app/dashboard/settings/page.tsx` — 设置页面下载位置管理增强
- `web-dashboard/src/app/dashboard/library/page.tsx` — 文件库页面增强

### 后端修改
- `backend/routers/download.py` — 下载路由增强（错误分类、状态细化）
- `backend/routers/settings.py` — 设置路由（已存在，无需修改）
- `backend/routers/library.py` — 文件库路由（已存在，无需修改）
- `core/audio_downloader.py` — 音频下载器（错误处理增强）

---

## Task 1: 修复并增强下载进度显示

**Files:**
- Modify: `web-dashboard/src/app/dashboard/search/page.tsx`
- Modify: `web-dashboard/src/components/DownloadManager.tsx`

**问题诊断:**
- 当前 `downloadTasks` 状态存在但 `DownloadManager` 组件未被实际渲染到页面中
- 搜索页面只有一个固定的右上角进度指示器，信息过于简略
- 进度条显示逻辑正确但缺少下载速度、剩余时间、文件大小等关键信息

- [ ] **Step 1: 在搜索页面集成 DownloadManager 组件**

在 `search/page.tsx` 中添加 `DownloadManager` 的显式渲染，并添加切换按钮：

```tsx
import DownloadManager from "@/components/DownloadManager";

// 在组件状态中添加
const [showDownloadManager, setShowDownloadManager] = useState(false);

// 在 JSX 中渲染
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

// 在下载进度指示器上添加点击展开功能
{downloadTasks.filter((t) => t.status === "processing").length > 0 && (
  <motion.div
    onClick={() => setShowDownloadManager(true)}
    className="fixed right-6 top-6 z-40 flex items-center gap-2 px-4 py-2 bg-white/[0.05] border border-white/[0.08] rounded-xl text-xs text-gray-400 cursor-pointer hover:bg-white/[0.08] transition"
  >
    <Loader2 className="w-4 h-4 animate-spin" />
    <span>{downloadTasks.filter((t) => t.status === "processing").length} 个下载中</span>
  </motion.div>
)}
```

- [ ] **Step 2: 增强 DownloadManager 进度显示信息**

修改 `DownloadManager.tsx`，添加下载速度、剩余时间、文件大小显示：

```tsx
// 在 DownloadTask 接口中添加
export interface DownloadTask {
  taskId: string;
  podcastTitle: string;
  episodeTitle?: string;
  status: string;
  progress: number;
  error?: string;
  result?: DownloadStatusResponse["result"];
  // 新增字段
  downloadedBytes?: number;
  totalBytes?: number;
  speed?: string; // 如 "1.5 MB/s"
  eta?: string; // 如 "2分30秒"
}
```

在进度显示区域增强：
```tsx
{task.status === "processing" && (
  <div className="mt-2">
    <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
      <span>{task.progress.toFixed(1)}%</span>
      <span className="flex items-center gap-2">
        {task.speed && <span>{task.speed}</span>}
        {task.eta && <span>剩余 {task.eta}</span>}
        {task.totalBytes && task.downloadedBytes && (
          <span>{formatBytes(task.downloadedBytes)} / {formatBytes(task.totalBytes)}</span>
        )}
      </span>
    </div>
    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <motion.div
        className="h-full bg-emerald-500 rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${task.progress}%` }}
        transition={{ duration: 0.3 }}
      />
    </div>
  </div>
)}
```

添加工具函数：
```tsx
function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}
```

- [ ] **Step 3: 在搜索页面状态更新中添加上下文信息**

修改 `search/page.tsx` 中的轮询逻辑，传递更多状态信息：

```tsx
setDownloadTasks((prev) =>
  prev.map((task) =>
    task.taskId === response.task_id
      ? {
          ...task,
          status: status.status,
          progress: status.progress || 0,
          downloadedBytes: status.downloaded_bytes,
          totalBytes: status.total_bytes,
          result: status.result,
          error: status.error,
        }
      : task
  )
);
```

- [ ] **Step 4: 构建并测试**

Run: `cd web-dashboard && npm run build`
Expected: 构建成功，无 TypeScript 错误

---

## Task 2: 修复核心下载功能错误处理

**Files:**
- Modify: `backend/routers/download.py`
- Modify: `core/audio_downloader.py`
- Modify: `web-dashboard/src/app/dashboard/search/page.tsx`

**问题诊断:**
- 后端 `_do_download` 使用裸 `except Exception` 捕获所有异常，错误信息不够具体
- 前端使用 `alert()` 显示错误，用户体验差
- 缺少对常见错误场景的分类处理（网络错误、存储不足、权限错误、RSS 解析失败等）

- [ ] **Step 1: 在后端添加错误分类**

修改 `backend/routers/download.py`：

```python
import errno

class DownloadErrorCategory:
    NETWORK_ERROR = "network_error"
    RSS_PARSE_ERROR = "rss_parse_error"
    STORAGE_ERROR = "storage_error"
    PERMISSION_ERROR = "permission_error"
    NOT_FOUND_ERROR = "not_found_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"

def _categorize_error(error: Exception) -> tuple[str, str]:
    """将异常分类为可处理的错误类型."""
    error_msg = str(error).lower()
    
    if isinstance(error, RSSParseError):
        return DownloadErrorCategory.RSS_PARSE_ERROR, f"RSS 解析失败: {error}"
    
    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
        return DownloadErrorCategory.NETWORK_ERROR, "网络连接失败，请检查网络后重试"
    
    if isinstance(error, requests.HTTPError):
        status = error.response.status_code if hasattr(error, 'response') else 0
        if status == 404:
            return DownloadErrorCategory.NOT_FOUND_ERROR, "音频文件在服务器上不存在 (404)"
        elif status >= 500:
            return DownloadErrorCategory.NETWORK_ERROR, f"音频服务器错误 ({status})，请稍后重试"
        return DownloadErrorCategory.NETWORK_ERROR, f"下载请求失败: HTTP {status}"
    
    if isinstance(error, OSError):
        if error.errno == errno.ENOSPC:
            return DownloadErrorCategory.STORAGE_ERROR, "磁盘空间不足，请清理后重试"
        elif error.errno == errno.EACCES or error.errno == errno.EPERM:
            return DownloadErrorCategory.PERMISSION_ERROR, "文件权限不足，无法写入下载目录"
        elif error.errno == errno.ENOENT:
            return DownloadErrorCategory.NOT_FOUND_ERROR, "下载目录不存在"
    
    if "timeout" in error_msg or "timed out" in error_msg:
        return DownloadErrorCategory.TIMEOUT_ERROR, "下载超时，请检查网络后重试"
    
    if "no space" in error_msg or "disk full" in error_msg:
        return DownloadErrorCategory.STORAGE_ERROR, "磁盘空间不足"
    
    return DownloadErrorCategory.UNKNOWN_ERROR, f"下载失败: {error}"
```

修改 `_do_download` 函数：

```python
async def _do_download(task_id: str, request: DownloadRequest):
    """后台执行下载任务."""
    try:
        jobs[task_id]["status"] = "processing"
        
        def progress_cb(progress: float, downloaded: int, total: int):
            update_progress(task_id, progress, downloaded, total)
        
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
        category, message = _categorize_error(e)
        logger.error("Download failed", error=message, category=category, task_id=task_id)
        jobs[task_id]["status"] = "failed"
        jobs[task_id]["error"] = message
        jobs[task_id]["error_category"] = category
```

- [ ] **Step 2: 更新 DownloadStatusResponse 模型**

```python
class DownloadStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float | None = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    result: dict | None = None
    error: str | None = None
    error_category: str | None = None  # 新增
```

- [ ] **Step 3: 在前端替换 alert 为优雅的通知组件**

修改 `search/page.tsx`，移除 `alert()` 调用，使用状态驱动的通知：

```tsx
// 添加通知状态
const [notifications, setNotifications] = useState<Array<{
  id: string;
  type: "success" | "error" | "info";
  message: string;
  taskId?: string;
}>>([]);

const addNotification = (type: "success" | "error" | "info", message: string, taskId?: string) => {
  const id = Math.random().toString(36).substr(2, 9);
  setNotifications((prev) => [...prev, { id, type, message, taskId }]);
  setTimeout(() => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, 5000);
};

// 在下载完成/失败时
if (status.status === "completed") {
  clearInterval(pollInterval);
  setDownloadingId(null);
  setDownloadSuccess(`《${status.result?.episode_title || "未知单集"}》下载完成`);
  addNotification("success", `下载完成: ${status.result?.episode_title || "文件"}`);
} else if (status.status === "failed") {
  clearInterval(pollInterval);
  setDownloadingId(null);
  const errorMsg = status.error || "未知错误";
  addNotification("error", `下载失败: ${errorMsg}`, response.task_id);
}
```

添加通知渲染 JSX：
```tsx
{/* Notifications */}
<div className="fixed bottom-6 right-6 z-50 space-y-2">
  <AnimatePresence>
    {notifications.map((n) => (
      <motion.div
        key={n.id}
        initial={{ opacity: 0, y: 20, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, x: 100 }}
        className={`px-4 py-3 rounded-xl border text-sm flex items-center gap-2 shadow-lg ${
          n.type === "success"
            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
            : n.type === "error"
            ? "bg-red-500/10 border-red-500/20 text-red-400"
            : "bg-blue-500/10 border-blue-500/20 text-blue-400"
        }`}
      >
        {n.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : n.type === "error" ? <AlertCircle className="w-4 h-4" /> : <Info className="w-4 h-4" />}
        <span>{n.message}</span>
      </motion.div>
    ))}
  </AnimatePresence>
</div>
```

- [ ] **Step 4: 构建并测试**

Run: `cd web-dashboard && npm run build`
Expected: 构建成功

---

## Task 3: 增强下载位置管理系统

**Files:**
- Modify: `web-dashboard/src/app/dashboard/settings/page.tsx`
- Modify: `backend/routers/settings.py`（可选，如需要添加更多验证）

**问题诊断:**
- 设置页面已有下载路径管理功能，但缺少：
  - 路径选择对话框（用户必须手动输入路径）
  - 路径存在性实时验证反馈
  - 磁盘空间检查
  - 路径变更确认对话框

- [ ] **Step 1: 添加路径选择对话框（使用原生文件选择器）**

由于浏览器安全限制无法直接选择文件夹，添加一个改进的路径输入方式：

```tsx
// 添加一个"选择文件夹"按钮，使用 input type="file" webkitdirectory 属性
const [showPathConfirm, setShowPathConfirm] = useState(false);
const [pendingPath, setPendingPath] = useState("");

// 路径变更确认对话框
{showPathConfirm && (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center"
  >
    <motion.div
      initial={{ scale: 0.9 }}
      animate={{ scale: 1 }}
      className="bg-[#0c0c0e] border border-gray-800 rounded-2xl p-6 max-w-md w-full mx-4"
    >
      <h4 className="text-sm font-medium text-white mb-2">确认更改下载位置？</h4>
      <p className="text-xs text-gray-500 mb-4">
        新位置: <span className="text-gray-300">{pendingPath}</span>
      </p>
      <p className="text-xs text-gray-600 mb-4">
        更改后，新下载的文件将保存到此位置。已有文件不会自动移动。
      </p>
      <div className="flex gap-3 justify-end">
        <button
          onClick={() => setShowPathConfirm(false)}
          className="px-4 py-2 text-xs text-gray-400 hover:text-white transition"
        >
          取消
        </button>
        <button
          onClick={async () => {
            setShowPathConfirm(false);
            // 执行保存
            await savePath(pendingPath);
          }}
          className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 hover:bg-emerald-500/20 transition"
        >
          确认更改
        </button>
      </div>
    </motion.div>
  </motion.div>
)}
```

- [ ] **Step 2: 添加实时路径验证反馈**

在路径输入框添加实时验证：

```tsx
const [pathValidation, setPathValidation] = useState<{
  valid: boolean;
  message: string;
  checking: boolean;
}>({ valid: true, message: "", checking: false });

const validatePathRealtime = async (path: string) => {
  if (!path.trim()) {
    setPathValidation({ valid: true, message: "", checking: false });
    return;
  }
  setPathValidation((prev) => ({ ...prev, checking: true }));
  try {
    const result = await validateDownloadPath(path.trim());
    setPathValidation({
      valid: result.valid,
      message: result.valid ? "路径可用" : (result.error || "路径无效"),
      checking: false,
    });
  } catch {
    setPathValidation({ valid: false, message: "验证失败", checking: false });
  }
};

// 使用 debounce
useEffect(() => {
  const timer = setTimeout(() => validatePathRealtime(customPath), 500);
  return () => clearTimeout(timer);
}, [customPath]);
```

- [ ] **Step 3: 构建并测试**

Run: `cd web-dashboard && npm run build`
Expected: 构建成功

---

## Task 4: 添加全面的错误处理与友好提示

**Files:**
- Modify: `web-dashboard/src/components/DownloadManager.tsx`
- Modify: `web-dashboard/src/components/EpisodeList.tsx`

**问题诊断:**
- EpisodeList 组件中当 `onDownload` prop 存在时，不显示任何本地加载状态
- 错误信息不够友好，缺少重试指引
- 缺少网络断开检测

- [ ] **Step 1: 在 EpisodeList 中添加独立下载状态显示**

即使使用 `onDownload` prop，也添加本地视觉反馈：

```tsx
const [pendingDownloads, setPendingDownloads] = useState<Set<number>>(new Set());

const handleDownload = async (episode: EpisodeItem) => {
  if (onDownload) {
    setPendingDownloads((prev) => new Set(prev).add(episode.index));
    onDownload(episode.index, episode.title);
    // 3秒后清除 pending 状态（假设父组件会更新真实状态）
    setTimeout(() => {
      setPendingDownloads((prev) => {
        const next = new Set(prev);
        next.delete(episode.index);
        return next;
      });
    }, 3000);
    return;
  }
  // ... 原有逻辑
};

// 在按钮渲染中
<button
  onClick={() => handleDownload(episode)}
  disabled={downloadingIndex === episode.index || pendingDownloads.has(episode.index)}
  className="..."
>
  {downloadingIndex === episode.index || pendingDownloads.has(episode.index) ? (
    <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
  ) : (
    <Download className="w-4 h-4 text-gray-400" />
  )}
</button>
```

- [ ] **Step 2: 在 DownloadManager 中添加错误分类图标和重试指引**

```tsx
const getErrorIcon = (category?: string) => {
  switch (category) {
    case "network_error": return <WifiOff className="w-4 h-4 text-red-400" />;
    case "storage_error": return <HardDrive className="w-4 h-4 text-red-400" />;
    case "permission_error": return <Lock className="w-4 h-4 text-red-400" />;
    case "rss_parse_error": return <Rss className="w-4 h-4 text-red-400" />;
    default: return <XCircle className="w-4 h-4 text-red-400" />;
  }
};

const getErrorAction = (category?: string): string => {
  switch (category) {
    case "network_error": return "请检查网络连接后重试";
    case "storage_error": return "请清理磁盘空间后重试";
    case "permission_error": return "请检查文件夹权限后重试";
    case "rss_parse_error": return "RSS 源可能已失效，请尝试其他播客";
    default: return "请重试或联系支持";
  }
};
```

- [ ] **Step 3: 构建并测试**

Run: `cd web-dashboard && npm run build`
Expected: 构建成功

---

## Task 5: 确保下载流程全透明（通知系统）

**Files:**
- Modify: `web-dashboard/src/app/dashboard/search/page.tsx`
- Modify: `web-dashboard/src/components/DownloadManager.tsx`

- [ ] **Step 1: 在搜索页面添加全局通知系统**

已在 Task 2 中实现基础通知，现在增强为支持操作按钮：

```tsx
interface Notification {
  id: string;
  type: "success" | "error" | "info";
  message: string;
  taskId?: string;
  actions?: Array<{
    label: string;
    onClick: () => void;
  }>;
}

// 错误通知添加"重试"和"查看"操作
addNotification("error", `下载失败: ${errorMsg}`, response.task_id, [
  {
    label: "重试",
    onClick: () => handleRetry(response.task_id),
  },
  {
    label: "查看详情",
    onClick: () => setShowDownloadManager(true),
  },
]);
```

- [ ] **Step 2: 在下载管理器中添加任务详情展开**

```tsx
const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);

// 在任务卡片上添加点击展开
<motion.div
  onClick={() => setExpandedTaskId(expandedTaskId === task.taskId ? null : task.taskId)}
  className="cursor-pointer"
>
  {/* ... */}
  <AnimatePresence>
    {expandedTaskId === task.taskId && (
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: "auto", opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        className="mt-2 pt-2 border-t border-white/[0.04]"
      >
        <p className="text-[10px] text-gray-600">任务 ID: {task.taskId}</p>
        {task.error && <p className="text-[10px] text-red-400 mt-1">{task.error}</p>}
      </motion.div>
    )}
  </AnimatePresence>
</motion.div>
```

- [ ] **Step 3: 构建并测试**

Run: `cd web-dashboard && npm run build`
Expected: 构建成功

---

## Task 6: 跨功能验证与测试

**Files:**
- Modify: `web-dashboard/src/app/dashboard/library/page.tsx`
- Modify: `backend/routers/library.py`（如需修复）

- [ ] **Step 1: 验证文件库与下载功能的联动**

确保下载完成的文件能在文件库中正确显示：

```tsx
// 在下载完成后刷新文件库（如果用户在文件库页面）
// 这需要在全局状态或事件总线中处理
```

- [ ] **Step 2: 验证"打开位置"功能跨平台兼容性**

检查 `library.py` 和 `download.py` 中的 `open-folder` 端点：
- Windows: `explorer /select,"path"` ✅
- macOS: `open -R path` ✅
- Linux: `xdg-open folder_path` ✅

- [ ] **Step 3: 手动测试清单**

1. 搜索播客 → 展开单集列表 → 点击下载 → 观察进度显示
2. 断开网络 → 尝试下载 → 观察错误提示和重试功能
3. 更改下载路径 → 验证路径验证 → 确认对话框
4. 下载完成后 → 点击"打开位置" → 验证文件夹打开
5. 检查文件库 → 验证新下载文件出现

---

## Task 7: 文档撰写

**Files:**
- Create: `docs/download-feature-guide.md`

- [ ] **Step 1: 编写用户指南**

```markdown
# 下载功能用户指南

## 如何下载播客单集

1. 在搜索框中输入播客名称
2. 点击搜索结果右侧的"列表"图标展开单集
3. 点击单集右侧的下载按钮
4. 在右上角或下载管理面板中查看进度

## 下载状态说明

- 🟡 下载中: 显示进度百分比、下载速度、剩余时间
- 🟢 已完成: 显示文件大小，可点击"打开位置"
- 🔴 失败: 显示错误原因和解决建议

## 常见问题

### 下载失败：网络错误
- 检查网络连接
- 点击"重试"按钮

### 下载失败：磁盘空间不足
- 清理磁盘空间
- 或在设置中更改下载位置

### 下载位置更改
1. 前往"系统设置" → "存储设置"
2. 输入新的下载目录路径
3. 点击"保存"
```

- [ ] **Step 2: 编写技术文档**

记录所有 API 端点、状态码、错误分类和前端状态管理逻辑。

---

## 执行检查清单

- [ ] Task 1 完成：下载进度显示增强
- [ ] Task 2 完成：核心下载错误处理
- [ ] Task 3 完成：下载位置管理增强
- [ ] Task 4 完成：全面错误处理
- [ ] Task 5 完成：通知系统完善
- [ ] Task 6 完成：跨功能验证
- [ ] Task 7 完成：文档撰写
- [ ] 构建通过：`npm run build`
- [ ] 手动测试通过
