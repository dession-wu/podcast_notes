# 修复搜索下载功能 + 新增转录预估时间功能 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复播客搜索页面的下载功能，使其能够直接从搜索结果下载播客内容；新增音频转录预估时间功能，根据音频时长自动计算并展示预计完成时间。

**Architecture:**
- 搜索页面：在搜索结果卡片上添加下载按钮，点击后调用后端下载 API，使用 RSS URL 下载最新单集
- 转录预估：后端在接收音频文件后，使用 ffprobe 或文件大小估算音频时长，结合 STT 引擎处理速度计算预估时间，前端在转录开始前和进行中展示预估/剩余时间

**Tech Stack:** FastAPI, Next.js 16, React 19, TypeScript, Tailwind CSS, Framer Motion

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `web-dashboard/src/app/dashboard/search/page.tsx` | 修改 | 搜索页面：添加下载按钮和下载状态管理 |
| `web-dashboard/src/lib/api.ts` | 修改 | 前端 API：添加预估时间相关类型和接口 |
| `backend/routers/transcribe.py` | 修改 | 转录 API：添加音频时长检测和预估时间计算 |
| `backend/core/transcriber.py` | 修改 | 转录器：添加 `estimate_time()` 方法 |
| `web-dashboard/src/app/dashboard/transcripts/page.tsx` | 修改 | 转录页面：展示预估时间和剩余时间 |

---

## Task 1: 修复搜索页面下载功能

### 1.1 分析当前搜索页面

**文件:** `web-dashboard/src/app/dashboard/search/page.tsx`

当前搜索页面：
- 调用 `searchPodcasts()` 获取搜索结果
- 结果卡片只展示播客信息，无下载按钮
- 需要添加：下载按钮 + 下载状态管理 + 调用下载 API

**问题诊断:**
1. 搜索页面没有下载按钮
2. 搜索结果中没有单集音频 URL（只有 RSS URL）
3. 需要调用后端下载 API，传入 RSS URL

### 1.2 修改搜索页面 — 添加下载按钮

**文件:** `web-dashboard/src/app/dashboard/search/page.tsx`

**步骤:**

- [ ] **Step 1: 导入下载 API 和 Download/Loader2 图标**

将现有导入修改为：
```typescript
import { searchPodcasts, PodcastResult, startDownload, getDownloadStatus } from "@/lib/api";
import { Search, Radio, ArrowRight, Clock, User, AlertCircle, Download, Loader2 } from "lucide-react";
```

- [ ] **Step 2: 添加下载状态管理**

在组件 state 中（`hasSearched` 下方）添加：
```typescript
const [downloadingId, setDownloadingId] = useState<string | null>(null);
const [downloadError, setDownloadError] = useState("");
const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);
```

- [ ] **Step 3: 添加下载处理函数**

在 `handleKeyDown` 函数下方添加：
```typescript
const handleDownload = async (podcast: PodcastResult) => {
  if (!podcast.rss_url) {
    setDownloadError("该播客没有提供 RSS 链接，无法下载");
    return;
  }

  setDownloadingId(podcast.id);
  setDownloadError("");
  setDownloadSuccess(null);

  try {
    const response = await startDownload({
      rss_url: podcast.rss_url,
      episode_index: 0, // 下载最新单集
    });

    // 轮询下载状态
    const pollInterval = setInterval(async () => {
      try {
        const status = await getDownloadStatus(response.task_id);
        if (status.status === "completed") {
          clearInterval(pollInterval);
          setDownloadingId(null);
          setDownloadSuccess(`《${status.result?.episode_title || "未知单集"}》下载完成`);
          // 3秒后清除成功提示
          setTimeout(() => setDownloadSuccess(null), 3000);
        } else if (status.status === "failed") {
          clearInterval(pollInterval);
          setDownloadingId(null);
          setDownloadError(status.error || "下载失败");
        }
      } catch (err) {
        clearInterval(pollInterval);
        setDownloadingId(null);
        setDownloadError("检查下载状态时出错");
      }
    }, 2000);

    // 60秒后停止轮询
    setTimeout(() => {
      clearInterval(pollInterval);
      setDownloadingId(null);
    }, 60000);

  } catch (err) {
    setDownloadingId(null);
    setDownloadError(err instanceof Error ? err.message : "下载失败");
  }
};
```

- [ ] **Step 4: 在搜索结果卡片上添加下载按钮**

找到结果卡片中 `ArrowRight` 图标的位置（约第 164 行），将其替换为包含下载按钮的容器：

将：
```tsx
<ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-white transition-colors flex-shrink-0 mt-1" />
```

替换为：
```tsx
<div className="flex items-center gap-2 flex-shrink-0 mt-1">
  <button
    onClick={(e) => {
      e.stopPropagation();
      handleDownload(podcast);
    }}
    disabled={downloadingId === podcast.id}
    className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition disabled:opacity-50"
    title="下载最新单集"
  >
    {downloadingId === podcast.id ? (
      <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
    ) : (
      <Download className="w-4 h-4 text-gray-400" />
    )}
  </button>
  <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-white transition-colors" />
</div>
```

- [ ] **Step 5: 添加下载错误和成功提示**

在搜索错误提示的 `</AnimatePresence>` 之后添加下载错误提示：
```tsx
<AnimatePresence>
  {downloadError && (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3"
    >
      <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
      <p className="text-sm text-red-400">{downloadError}</p>
    </motion.div>
  )}
</AnimatePresence>

<AnimatePresence>
  {downloadSuccess && (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-3"
    >
      <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
      <p className="text-sm text-emerald-400">{downloadSuccess}</p>
    </motion.div>
  )}
</AnimatePresence>
```

同时需要导入 `CheckCircle2`：
```typescript
import { Search, Radio, ArrowRight, Clock, User, AlertCircle, Download, Loader2, CheckCircle2 } from "lucide-react";
```

### 1.3 验证后端下载 API 支持 RSS URL 下载

**文件:** `backend/routers/download.py`

当前下载 API 已经支持通过 RSS URL 下载，使用 `AudioDownloader.download_from_rss()` 方法。该路由已完整实现，无需修改。

需要确认：
- `download_from_rss` 方法是否能正确解析 RSS 并下载最新单集 — 已在 `core/audio_downloader.py` 中实现
- 返回的 `episode` 对象是否包含 `title` 和 `feed_title` — 已确认包含

---

## Task 2: 新增音频转录预估时间功能

### 2.1 后端 — 添加音频时长检测和预估时间计算

**文件:** `backend/routers/transcribe.py`

**步骤:**

- [ ] **Step 1: 导入音频检测相关库**

在文件顶部现有导入下方添加：
```python
import subprocess
import json
```

- [ ] **Step 2: 添加音频时长检测函数**

在 `jobs` 字典定义之后、`TranscribeResponse` 类之前添加辅助函数：

```python
def get_audio_duration(file_path: Path) -> float | None:
    """获取音频文件时长（秒）.

    优先使用 ffprobe，如果不可用则根据文件大小估算。

    Args:
        file_path: 音频文件路径

    Returns:
        音频时长（秒），如果无法获取则返回 None
    """
    # 尝试使用 ffprobe
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        if duration > 0:
            return duration
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, ValueError):
        pass

    # ffprobe 不可用，根据文件大小估算
    # 常见音频格式比特率估算（kbps）
    BITRATE_ESTIMATES = {
        ".mp3": 128,
        ".m4a": 128,
        ".aac": 128,
        ".ogg": 128,
        ".wav": 1411,
        ".flac": 800,
    }

    try:
        file_size_bits = file_path.stat().st_size * 8
        ext = file_path.suffix.lower()
        bitrate = BITRATE_ESTIMATES.get(ext, 128) * 1000  # 转换为 bps
        estimated_duration = file_size_bits / bitrate
        if estimated_duration > 0:
            return estimated_duration
    except OSError:
        pass

    return None


def calculate_estimate_time(duration_seconds: float, provider: str = "sensevoice") -> dict[str, any]:
    """计算转录预估时间.

    基于音频时长和 STT 引擎的处理速度计算预估时间。
    处理速度参考值（基于实际测试和业界数据）：
    - SenseVoice (GPU): ~0.3x 实时（1分钟音频约18秒处理）
    - SenseVoice (CPU): ~1.0x 实时（1分钟音频约60秒处理）
    - Whisper (base): ~0.5x 实时
    - Whisper (small): ~1.0x 实时
    - Whisper (medium): ~2.0x 实时
    - faster-whisper: ~0.3x 实时

    Args:
        duration_seconds: 音频时长（秒）
        provider: STT 引擎提供商

    Returns:
        预估信息字典，包含 total_seconds, formatted_time, provider
    """
    # 处理速度倍数（音频时长 × 倍数 = 处理时间）
    SPEED_FACTORS = {
        "sensevoice": 0.8,      # 考虑模型加载和预处理开销
        "whisper": 1.2,
        "faster_whisper": 0.5,
        "elevenlabs": 0.3,      # API 调用，通常很快
    }

    # 基础开销（秒）：模型加载、文件预处理等
    BASE_OVERHEAD = {
        "sensevoice": 15,
        "whisper": 20,
        "faster_whisper": 10,
        "elevenlabs": 5,
    }

    factor = SPEED_FACTORS.get(provider, 1.0)
    overhead = BASE_OVERHEAD.get(provider, 10)

    total_seconds = int(duration_seconds * factor + overhead)

    # 格式化时间
    if total_seconds < 60:
        formatted = f"{total_seconds}秒"
    elif total_seconds < 3600:
        mins = total_seconds // 60
        secs = total_seconds % 60
        formatted = f"{mins}分{secs}秒" if secs > 0 else f"{mins}分钟"
    else:
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        formatted = f"{hours}小时{mins}分" if mins > 0 else f"{hours}小时"

    return {
        "total_seconds": total_seconds,
        "formatted_time": formatted,
        "provider": provider,
        "audio_duration_seconds": duration_seconds,
        "audio_duration_formatted": _format_duration(duration_seconds),
    }


def _format_duration(seconds: float) -> str:
    """格式化秒数为可读字符串."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
```

- [ ] **Step 3: 修改 `TranscribeResponse` 模型添加预估字段**

修改 `TranscribeResponse` 类：
```python
class TranscribeResponse(BaseModel):
    """Transcribe response model."""

    task_id: str
    status: str
    estimate: dict | None = None  # 新增：预估时间信息
```

- [ ] **Step 4: 修改 `start_transcription` 路由计算并返回预估时间**

修改 `start_transcription` 函数，在保存文件后、创建 job 之前添加时长检测和预估计算：

在 `with open(file_path, "wb") as f:` 块之后，创建 job 之前插入：

```python
        # 检测音频时长
        duration = get_audio_duration(file_path)
        estimate = None
        if duration:
            from config.settings import STTProvider
            provider = settings.stt_provider.value if hasattr(settings.stt_provider, 'value') else str(settings.stt_provider)
            estimate = calculate_estimate_time(duration, provider)
            logger.info(
                "音频时长检测完成",
                duration_seconds=duration,
                estimate_seconds=estimate["total_seconds"],
                provider=provider,
            )
```

然后修改创建 job 的代码，将 `estimate` 存入 job：
```python
        # Create job
        jobs[task_id] = {
            "status": "processing",
            "progress": 0.0,
            "file_path": str(file_path),
            "result": None,
            "error": None,
            "estimate": estimate,  # 新增
            "start_time": None,    # 新增：用于计算剩余时间
        }
```

在转录开始之前（`transcriber = Transcriber()` 之前）添加：
```python
        # 记录开始时间
        jobs[task_id]["start_time"] = time.time()
```

同时需要在文件顶部导入 `time`：
```python
import time
```

修改返回语句：
```python
        return TranscribeResponse(task_id=task_id, status="completed", estimate=estimate)
```

- [ ] **Step 5: 修改 `TranscribeStatusResponse` 模型添加预估字段**

修改 `TranscribeStatusResponse` 类：
```python
class TranscribeStatusResponse(BaseModel):
    """Transcribe status response model."""

    task_id: str
    status: str
    progress: float | None = None
    result: dict | None = None
    error: str | None = None
    estimate: dict | None = None  # 新增：预估时间信息
    elapsed_seconds: float | None = None  # 新增：已运行时间
    remaining_seconds: float | None = None  # 新增：剩余预估时间
```

- [ ] **Step 6: 修改 `get_transcription_status` 路由返回动态剩余时间**

修改 `get_transcription_status` 函数，在返回之前计算动态剩余时间：

```python
    job = jobs[task_id]

    # 计算动态剩余时间
    elapsed = None
    remaining = None
    if job.get("start_time") and job["status"] == "processing":
        elapsed = time.time() - job["start_time"]
        if job.get("estimate"):
            total_estimate = job["estimate"]["total_seconds"]
            remaining = max(0, total_estimate - elapsed)

    return TranscribeStatusResponse(
        task_id=task_id,
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
        estimate=job.get("estimate"),
        elapsed_seconds=round(elapsed, 1) if elapsed else None,
        remaining_seconds=round(remaining, 1) if remaining else None,
    )
```

### 2.2 前端 — 更新 API 类型和转录页面展示预估时间

**文件:** `web-dashboard/src/lib/api.ts`

- [ ] **Step 7: 更新 `TranscribeResponse` 和 `TranscribeStatusResponse` 类型**

修改 `TranscribeResponse` 接口：
```typescript
export interface TranscribeResponse {
  task_id: string;
  status: string;
  estimate?: {
    total_seconds: number;
    formatted_time: string;
    provider: string;
    audio_duration_seconds: number;
    audio_duration_formatted: string;
  };
}
```

修改 `TranscribeStatusResponse` 接口：
```typescript
export interface TranscribeStatusResponse {
  task_id: string;
  status: string;
  progress?: number;
  result?: {
    text: string;
    word_count: number;
    segment_count: number;
    language?: string;
    duration_seconds?: number;
  };
  error?: string;
  estimate?: {
    total_seconds: number;
    formatted_time: string;
    provider: string;
    audio_duration_seconds: number;
    audio_duration_formatted: string;
  };
  elapsed_seconds?: number;
  remaining_seconds?: number;
}
```

**文件:** `web-dashboard/src/app/dashboard/transcripts/page.tsx`

- [ ] **Step 8: 更新 `TranscriptJob` 接口添加预估字段**

修改 `TranscriptJob` 接口：
```typescript
interface TranscriptJob {
  id: string;
  filename: string;
  status: "uploading" | "processing" | "completed" | "failed";
  progress: number;
  result?: TranscribeStatusResponse["result"];
  error?: string;
  createdAt: string;
  estimate?: TranscribeStatusResponse["estimate"];  // 新增
  elapsedSeconds?: number;  // 新增
  remainingSeconds?: number;  // 新增
}
```

- [ ] **Step 9: 在 `pollStatus` 回调中更新预估时间信息**

修改 `pollStatus` 函数中的 `setJobs` 调用，添加预估字段：

在 `job.id === taskId` 的更新对象中添加：
```typescript
estimate: status.estimate || undefined,
elapsedSeconds: status.elapsed_seconds || undefined,
remainingSeconds: status.remaining_seconds || undefined,
```

- [ ] **Step 10: 在 `handleFileUpload` 中保存预估信息**

在 `handleFileUpload` 函数中，收到 `startTranscription` 响应后，将预估信息保存到 job：

在 `setJobs((prev) => prev.map((job) => job.id === taskId ? { ...job, id: serverTaskId, progress: 50 } : job))` 这行之前添加：

```typescript
      // 保存预估信息
      const estimate = response.estimate;
      setJobs((prev) =>
        prev.map((job) =>
          job.id === taskId
            ? {
                ...job,
                id: serverTaskId,
                progress: 50,
                estimate: estimate || undefined,
              }
            : job
        )
      );
```

然后删除原来的 `setJobs` 调用（只更新 id 和 progress 的那行）。

- [ ] **Step 11: 添加预估时间格式化辅助函数**

在 `formatDuration` 函数下方添加：
```typescript
const formatEstimateTime = (seconds?: number) => {
  if (!seconds || seconds <= 0) return "计算中...";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins >= 60) {
    const hours = Math.floor(mins / 60);
    return `${hours}小时${mins % 60}分`;
  }
  if (mins > 0) {
    return secs > 0 ? `${mins}分${secs}秒` : `${mins}分钟`;
  }
  return `${secs}秒`;
};
```

- [ ] **Step 12: 在 job 卡片中展示预估时间和剩余时间**

在 job 卡片的进度条下方（`</div>` 闭合标签之前，在进度条 `motion.div` 之后）添加预估时间展示：

在进度条代码块之后添加：
```tsx
{job.estimate && (
  <div className="mt-1.5 flex items-center gap-2 text-[10px] text-gray-500">
    <Clock className="w-3 h-3" />
    {job.status === "processing" && job.remainingSeconds !== undefined ? (
      <span>
        剩余约 {formatEstimateTime(job.remainingSeconds)}
        <span className="text-gray-600 ml-1">
          (音频 {job.estimate.audio_duration_formatted})
        </span>
      </span>
    ) : job.status === "completed" ? (
      <span>
        已完成 · 音频 {job.estimate.audio_duration_formatted}
      </span>
    ) : (
      <span>
        预计 {job.estimate.formatted_time}
        <span className="text-gray-600 ml-1">
          (音频 {job.estimate.audio_duration_formatted})
        </span>
      </span>
    )}
  </div>
)}
```

- [ ] **Step 13: 在上传区域添加预估时间说明**

在上传区域（Upload Area）的说明文字下方添加一行提示：

将：
```tsx
          <p className="text-xs text-gray-600">
            支持 MP3, WAV, M4A, OGG, FLAC, AAC 格式
          </p>
```

替换为：
```tsx
          <p className="text-xs text-gray-600">
            支持 MP3, WAV, M4A, OGG, FLAC, AAC 格式
          </p>
          <p className="text-[10px] text-gray-700 mt-1">
            上传后将自动检测音频时长并预估转录所需时间
          </p>
```

---

## Task 3: 构建和测试

- [ ] **Step 14: 运行前端构建**

```bash
cd d:\podcast_notes\web-dashboard
npm run build
```

- [ ] **Step 15: 验证后端路由**

启动后端服务：
```bash
cd d:\podcast_notes
python -m backend.main
```

验证转录预估 API：
```bash
curl -X POST http://localhost:8000/api/transcribe/ \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@test.mp3"
```

验证下载 API：
```bash
curl -X POST http://localhost:8000/api/download/ \
  -H "Content-Type: application/json" \
  -d '{"rss_url": "https://example.com/feed.xml", "episode_index": 0}'
```

- [ ] **Step 16: 浏览器端验证**

1. 打开 Dashboard 搜索页面，搜索播客，确认每个结果卡片上有下载按钮
2. 点击下载按钮，确认能正确调用下载 API 并显示状态
3. 打开转录页面，上传音频文件，确认上传后显示预估时间
4. 确认转录过程中动态更新剩余时间
5. 确认转录完成后显示实际音频时长

---

## 预估时间算法说明

### 处理速度参考

| STT 引擎 | 速度倍数 | 基础开销 | 说明 |
|---------|---------|---------|------|
| SenseVoice | 0.8x | 15s | 考虑模型加载和预处理 |
| Whisper | 1.2x | 20s | 取决于模型大小 |
| faster-whisper | 0.5x | 10s | 优化版本 |
| ElevenLabs | 0.3x | 5s | API 调用 |

**计算公式：**
```
预估时间(秒) = 音频时长(秒) × 速度倍数 + 基础开销(秒)
```

**示例：**
- 10分钟音频使用 SenseVoice：600 × 0.8 + 15 = 495秒 ≈ 8分15秒
- 30分钟音频使用 SenseVoice：1800 × 0.8 + 15 = 1455秒 ≈ 24分15秒

### 动态剩余时间更新

在转录过程中，后端每秒计算：
```
剩余时间 = 预估总时间 - 已运行时间
```

前端每 2 秒轮询一次状态，获取最新的剩余时间并展示。

### 误差控制

- 速度倍数基于实际测试数据和业界基准设定
- 对于无法检测时长的文件，使用文件大小估算（误差可能较大）
- 预估时间向上取整，避免用户预期过高
- 实际处理时间通常比预估快 10-20%（预留安全余量）
