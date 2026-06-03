# 转录文本查看功能修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复转录完成后文本查看功能不可用的问题，确保用户能够清晰、完整地查看、复制和下载转录文本。

**Architecture:** 通过排查发现，转录文本查看功能的前端组件（TranscriptViewer）和调用逻辑都已实现，但存在数据流和状态管理问题。修复方案包括：1) 为转录文件（.md）添加直接查看功能；2) 修复音频文件转录状态的持久化和恢复逻辑；3) 增强错误处理和用户反馈。

**Tech Stack:** Next.js 14 (App Router), React, TypeScript, Tailwind CSS, Framer Motion, Lucide React

---

## 问题诊断总结

基于代码审查和截图分析，发现以下问题：

1. **转录文件（.md）缺少查看入口**：在资料库页面中，转录文件（`transcript` 类型）没有提供查看文本的按钮，用户无法直接打开转录内容。

2. **音频文件转录状态丢失**：当用户刷新页面或切换标签后，音频文件的转录任务状态（`transcriptionTasks`）虽然从 `localStorage` 恢复，但可能与实际的文件列表不匹配，导致"查看文本"按钮不显示。

3. **转录文件没有关联的转录任务**：转录文件（.md）是通过后端扫描文件系统发现的，它们没有对应的 `transcriptionTasks` 记录，因此无法使用 `TranscriptViewer` 查看。

4. **缺少从文件直接读取文本的逻辑**：当前 `TranscriptViewer` 只能通过 `transcriptionTasks` 的 `result.text` 获取文本，没有直接从 `.md` 文件读取内容的途径。

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `web-dashboard/src/app/dashboard/library/page.tsx` | 修改 | 资料库页面主组件，添加转录文件查看逻辑 |
| `web-dashboard/src/components/TranscriptViewer.tsx` | 修改 | 增强查看器，支持直接从文件路径加载文本 |
| `web-dashboard/src/lib/api.ts` | 修改 | 添加读取转录文件内容的 API 函数 |
| `backend/routers/library.py` | 修改 | 添加读取转录文件文本内容的端点 |

---

## Task 1: 后端添加转录文件内容读取端点

**Files:**
- Modify: `backend/routers/library.py`

- [ ] **Step 1: 添加读取转录文件内容的 API 端点**

在 `backend/routers/library.py` 中添加新端点：

```python
@router.get("/transcript-content/{file_id}")
async def get_transcript_content(file_id: str):
    """读取转录文件（.md 或 .txt）的文本内容"""
    data_dir = _get_data_dir()
    transcripts_dir = data_dir / "transcripts"
    
    if not transcripts_dir.exists():
        raise HTTPException(status_code=404, detail="Transcripts directory not found")
    
    # 查找匹配的文件（file_id 格式: transcript_{stem}_{mtime}）
    for entry in transcripts_dir.iterdir():
        if entry.is_file():
            stat = entry.stat()
            entry_id = f"transcript_{entry.stem}_{stat.st_mtime}"
            if entry_id == file_id:
                try:
                    content = entry.read_text(encoding="utf-8")
                    return {
                        "file_id": file_id,
                        "file_name": entry.name,
                        "content": content,
                        "word_count": len(content),
                    }
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    
    raise HTTPException(status_code=404, detail="Transcript file not found")
```

- [ ] **Step 2: 验证后端端点**

运行测试命令：
```bash
curl "http://localhost:8001/api/library/transcript-content/transcript_Stranded_in_the_Strait_of_Hormuz_mp3_transcript_1751174400.0"
```

Expected: 返回 JSON 包含 `content` 字段

---

## Task 2: 前端添加读取转录文件内容的 API 函数

**Files:**
- Modify: `web-dashboard/src/lib/api.ts`

- [ ] **Step 1: 添加 `getTranscriptContent` 函数**

在 `web-dashboard/src/lib/api.ts` 中添加：

```typescript
export interface TranscriptContentResponse {
  file_id: string;
  file_name: string;
  content: string;
  word_count: number;
}

export async function getTranscriptContent(fileId: string): Promise<TranscriptContentResponse> {
  return fetchApi<TranscriptContentResponse>(`/api/library/transcript-content/${fileId}`);
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

运行：
```bash
cd web-dashboard && npx tsc --noEmit
```

Expected: 无编译错误

---

## Task 3: 增强 TranscriptViewer 组件

**Files:**
- Modify: `web-dashboard/src/components/TranscriptViewer.tsx`

- [ ] **Step 1: 添加直接从内容渲染的模式**

修改 `TranscriptViewerProps` 接口，支持两种模式：

```typescript
interface TranscriptViewerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  text?: string;
  fileId?: string;
  metadata?: {
    word_count?: number;
    language?: string;
    engine_used?: string;
    duration_seconds?: number;
  } | null;
}
```

- [ ] **Step 2: 添加从文件加载内容的逻辑**

在组件内部添加：

```typescript
export default function TranscriptViewer({
  isOpen,
  onClose,
  title,
  text: initialText,
  fileId,
  metadata,
}: TranscriptViewerProps) {
  const [copied, setCopied] = useState(false);
  const [text, setText] = useState(initialText || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (fileId && !initialText) {
      setLoading(true);
      getTranscriptContent(fileId)
        .then((res) => {
          setText(res.content);
        })
        .catch((err) => {
          setError(err.message || "加载失败");
        })
        .finally(() => {
          setLoading(false);
        });
    } else if (initialText) {
      setText(initialText);
    }
  }, [fileId, initialText, isOpen]);
  
  // ... rest of component
}
```

- [ ] **Step 3: 添加加载和错误状态 UI**

在内容区域添加加载指示器和错误提示：

```tsx
{/* Content */}
<div className="flex-1 overflow-y-auto p-4">
  {loading ? (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="w-6 h-6 text-gray-600 animate-spin" />
      <span className="ml-2 text-sm text-gray-500">加载文本...</span>
    </div>
  ) : error ? (
    <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
      <AlertCircle className="w-4 h-4 text-red-400" />
      <span className="text-sm text-red-400">{error}</span>
    </div>
  ) : (
    <div className="prose prose-invert prose-sm max-w-none">
      <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
        {text}
      </p>
    </div>
  )}
</div>
```

---

## Task 4: 修改资料库页面，为转录文件添加查看功能

**Files:**
- Modify: `web-dashboard/src/app/dashboard/library/page.tsx`

- [ ] **Step 1: 为转录文件添加"查看文本"按钮**

在文件列表渲染逻辑中，为 `transcript` 类型的文件添加查看按钮：

找到这段代码（约第 516-552 行）：
```tsx
<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
  {/* Transcribe button for audio files */}
  {isAudio && !task && (
    <button...>
  )}
  <button onClick={() => handleOpenLocation(file)}...>
  <button className="..." title="删除">
</div>
```

修改为：
```tsx
<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
  {/* Transcribe button for audio files */}
  {isAudio && !task && (
    <button...>
  )}
  
  {/* View transcript button for transcript files */}
  {file.type === "transcript" && (
    <button
      onClick={() => handleViewTranscriptFile(file)}
      className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 transition"
      title="查看文本"
    >
      <FileText className="w-3.5 h-3.5 text-emerald-400" />
      <span className="text-xs text-emerald-400">查看文本</span>
    </button>
  )}
  
  <button onClick={() => handleOpenLocation(file)}...>
  <button className="..." title="删除">
</div>
```

- [ ] **Step 2: 添加 `handleViewTranscriptFile` 处理函数**

在组件中添加新函数：

```typescript
const handleViewTranscriptFile = (file: LibraryFile) => {
  setViewerTask({
    fileId: file.id,
    taskId: `file_${file.id}`,
    status: "completed",
    progress: 100,
    result: null, // Will be loaded by TranscriptViewer
    error: null,
    errorCategory: null,
    estimate: null,
    elapsedSeconds: null,
    remainingSeconds: null,
  });
  setViewerOpen(true);
};
```

- [ ] **Step 3: 修改 TranscriptViewer 的调用，传递 fileId**

修改 TranscriptViewer 的调用：

```tsx
<TranscriptViewer
  isOpen={viewerOpen}
  onClose={handleCloseViewer}
  title={files.find(f => f.id === viewerTask?.fileId)?.episode_title || "转录文本"}
  text={viewerTask?.result?.text || ""}
  fileId={!viewerTask?.result?.text ? viewerTask?.fileId : undefined}
  metadata={viewerTask?.result ? {
    word_count: viewerTask.result.word_count,
    language: viewerTask.result.language,
    engine_used: viewerTask.result.engine_used,
    duration_seconds: viewerTask.result.duration_seconds,
  } : null}
/>
```

---

## Task 5: 修复音频文件转录状态持久化问题

**Files:**
- Modify: `web-dashboard/src/app/dashboard/library/page.tsx`

- [ ] **Step 1: 在加载文件列表时恢复转录状态**

修改 `fetchFiles` 函数，在获取文件列表后，检查每个音频文件是否已有转录文件：

```typescript
const fetchFiles = useCallback(async () => {
  const currentVersion = ++fetchVersionRef.current;
  setLoading(true);
  setError("");
  try {
    const res = await getLibraryFiles(activeTab, searchQuery, sortBy, timeRange);
    if (currentVersion !== fetchVersionRef.current) return;
    setFiles(res.files);
    setTypeCounts(res.type_counts);
    
    // Check for completed transcriptions that exist as files but not in tasks
    const storedTasks = getStoredTranscriptionTasks();
    const updatedTasks = { ...storedTasks };
    
    for (const file of res.files) {
      if (file.type === "audio") {
        // Check if there's a corresponding transcript file
        const transcriptFile = res.files.find(
          f => f.type === "transcript" && f.name.includes(file.name.replace(/\.[^.]+$/, ""))
        );
        
        if (transcriptFile && !updatedTasks[file.id]) {
          // Create a completed task for this audio file
          updatedTasks[file.id] = {
            fileId: file.id,
            taskId: `file_${transcriptFile.id}`,
            status: "completed",
            progress: 100,
            result: null,
            error: null,
            errorCategory: null,
            estimate: null,
            elapsedSeconds: null,
            remainingSeconds: null,
          };
        }
      }
    }
    
    if (Object.keys(updatedTasks).length > Object.keys(storedTasks).length) {
      setTranscriptionTasks(updatedTasks);
      // Persist to localStorage
      Object.entries(updatedTasks).forEach(([fileId, task]) => {
        if (!storedTasks[fileId]) {
          saveTranscriptionTask(task);
        }
      });
    }
  } catch (err: any) {
    if (currentVersion !== fetchVersionRef.current) return;
    setError(err.message || "加载失败");
  } finally {
    if (currentVersion === fetchVersionRef.current) {
      setLoading(false);
    }
  }
}, [activeTab, searchQuery, sortBy, timeRange]);
```

---

## Task 6: 功能测试

- [ ] **Step 1: 测试转录文件查看功能**

1. 访问 http://localhost:3002/dashboard/library
2. 点击"转录"标签
3. 点击转录文件旁边的"查看文本"按钮
4. 验证 TranscriptViewer 弹窗正确显示文本内容

- [ ] **Step 2: 测试音频文件转录后查看功能**

1. 点击"音频"标签
2. 对音频文件点击"转录"按钮
3. 等待转录完成
4. 点击"查看文本"按钮
5. 验证 TranscriptViewer 弹窗正确显示转录文本

- [ ] **Step 3: 测试不同状态下的界面表现**

| 状态 | 预期表现 |
|------|----------|
| 转录进行中 | 显示进度条，无"查看文本"按钮 |
| 转录完成 | 显示"查看文本"和"生成笔记"按钮 |
| 转录失败 | 显示错误信息和"重试"按钮 |
| 刷新页面后 | 已完成的转录仍显示"查看文本"按钮 |

- [ ] **Step 4: 测试复制和下载功能**

1. 打开 TranscriptViewer
2. 点击"复制"按钮，验证文本被复制到剪贴板
3. 点击"下载"按钮，验证文件被正确下载

---

## 执行命令汇总

```bash
# 1. 验证 TypeScript 编译
cd web-dashboard && npx tsc --noEmit

# 2. 重启前端开发服务器
cd web-dashboard && $env:PORT=3002; npm run dev

# 3. 测试后端 API
curl "http://localhost:8001/api/library/transcript-content/transcript_test_123"

# 4. 运行全链路测试
# - 访问 http://localhost:3002/dashboard/library
# - 测试转录文件查看
# - 测试音频转录后查看
```

---

## 成功标准

- [ ] 转录文件（.md）在资料库中显示"查看文本"按钮
- [ ] 点击"查看文本"按钮后，TranscriptViewer 正确显示完整文本
- [ ] 音频文件转录完成后，"查看文本"按钮可用
- [ ] 刷新页面后，已完成的转录状态仍然保留
- [ ] 复制和下载功能正常工作
- [ ] 不同转录状态（进行中/完成/失败）的界面表现正确