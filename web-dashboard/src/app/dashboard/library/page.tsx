"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderOpen,
  Search,
  Music,
  FileText,
  Image,
  Clock,
  HardDrive,
  ArrowUpDown,
  Calendar,
  Trash2,
  ExternalLink,
  Loader2,
  AlertCircle,
  Mic,
  CheckCircle2,
  XCircle,
  RotateCcw,
  ChevronDown,
} from "lucide-react";
import DevBanner from "@/components/DevBanner";
import {
  getLibraryFiles,
  LibraryFile,
  startTranscriptionByPath,
  getTranscriptionStatus,
  TranscribeStatusResponse,
  deleteLibraryFile,
  openLibraryLocation,
  uploadAudio,
  ApiError,
} from "@/lib/api";
import {
  getStoredTranscriptionTasks,
  saveTranscriptionTask,
  updateTranscriptionTask,
} from "@/lib/transcriptionStorage";
import TranscriptionProgress from "@/components/TranscriptionProgress";
import TranscriptViewer from "@/components/TranscriptViewer";

const tabs = [
  { key: "all", label: "全部", icon: FolderOpen },
  { key: "audio", label: "音频", icon: Music },
  { key: "transcript", label: "转录", icon: FileText },
  { key: "image", label: "图片", icon: Image },
];

const sortOptions = [
  { key: "time_desc", label: "最新优先" },
  { key: "time_asc", label: "最早优先" },
  { key: "name", label: "名称" },
  { key: "size", label: "大小" },
];

const timeRanges = [
  { key: "all", label: "全部时间" },
  { key: "today", label: "今天" },
  { key: "week", label: "本周" },
  { key: "month", label: "本月" },
];

const typeConfig: Record<string, { icon: any; color: string; bg: string; label: string }> = {
  audio: { icon: Music, color: "text-blue-400", bg: "bg-blue-400/10", label: "音频" },
  transcript: { icon: FileText, color: "text-emerald-400", bg: "bg-emerald-400/10", label: "转录" },
  image: { icon: Image, color: "text-purple-400", bg: "bg-purple-400/10", label: "图片" },
};

interface TranscriptionTask {
  fileId: string;
  taskId: string;
  status: string;
  progress: number;
  stage?: string | null;
  result: {
    text: string;
    word_count: number;
    segment_count?: number;
    language: string | null;
    duration_seconds?: number | null;
    engine_used?: string | null;
    language_detected?: string | null;
    detection_method?: string | null;
  } | null;
  error: string | null;
  errorCategory: string | null;
  errorDetail?: string | null;
  estimate: {
    total_seconds: number;
    formatted_time: string;
    provider?: string;
    audio_duration_seconds?: number;
    audio_duration_formatted?: string;
    speed_factor?: number;
    has_cuda?: boolean;
  } | null;
  elapsedSeconds: number | null;
  remainingSeconds: number | null;
}

export default function LibraryPage() {
  const [activeTab, setActiveTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("time_desc");
  const [timeRange, setTimeRange] = useState("all");
  const [files, setFiles] = useState<LibraryFile[]>([]);
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [transcribingId, setTranscribingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [transcriptionTasks, setTranscriptionTasks] = useState<Record<string, TranscriptionTask>>({});
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerTask, setViewerTask] = useState<TranscriptionTask | null>(null);
  const [uploading, setUploading] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (audio?: File) => {
    if (!audio) return;
    if (audio.size > 50 * 1024 * 1024) { setError("音频不能超过 50 MB"); return; }
    setUploading(true);
    setError("");
    try {
      const response = await uploadAudio(audio);
      const library = await getLibraryFiles();
      const file = library.files.find((item) => item.type === "audio" && item.name.startsWith(response.task_id));
      if (file) {
        const task: TranscriptionTask = {
          fileId: file.id, taskId: response.task_id, status: "processing", progress: 0,
          result: null, error: null, errorCategory: null, estimate: response.estimate,
          elapsedSeconds: null, remainingSeconds: response.estimate?.total_seconds ?? null,
        };
        setTranscriptionTasks((prev) => ({...prev, [file.id]: task}));
        saveTranscriptionTask(task);
      }
      setFiles(library.files);
      setTypeCounts(library.type_counts);
      setActiveTab("all");
      setSearchQuery("");
      setTimeRange("all");
    } catch (err) { setError(err instanceof Error ? err.message : "上传失败，请重试"); }
    finally { setUploading(false); if (uploadRef.current) uploadRef.current.value = ""; }
  };

  // Load persisted transcription tasks on mount
  useEffect(() => {
    const stored = getStoredTranscriptionTasks();
    if (Object.keys(stored).length > 0) {
      setTranscriptionTasks(stored as Record<string, TranscriptionTask>);
    }
  }, []);

  // Use a ref to track the latest request and prevent race conditions
  const fetchVersionRef = useRef(0);

  const fetchFiles = useCallback(async () => {
    const currentVersion = ++fetchVersionRef.current;
    setLoading(true);
    setError("");
    try {
      const res = await getLibraryFiles(activeTab, searchQuery, sortBy, timeRange);
      // Ignore stale responses
      if (currentVersion !== fetchVersionRef.current) return;
      setFiles(res.files);
      setTypeCounts(res.type_counts);

      // Check for completed transcriptions that exist as files but not in tasks
      const storedTasks = getStoredTranscriptionTasks();
      const updatedTasks = { ...storedTasks };
      let hasNewTasks = false;

      for (const file of res.files) {
        if (file.type === "audio") {
          // Check if there's a corresponding transcript file
          const audioStem = file.name.replace(/\.[^.]+$/, "");
          const transcriptFile = res.files.find(
            (f) => f.type === "transcript" && f.name.includes(audioStem)
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
            hasNewTasks = true;
          }
        }
      }

      if (hasNewTasks) {
        setTranscriptionTasks((prev) => ({ ...prev, ...updatedTasks }));
        // Persist to localStorage
        Object.entries(updatedTasks).forEach(([fileId, task]) => {
          if (!storedTasks[fileId]) {
            saveTranscriptionTask(task);
          }
        });
      }
    } catch (err: any) {
      // Ignore stale errors
      if (currentVersion !== fetchVersionRef.current) return;
      setError(err.message || "加载失败");
    } finally {
      if (currentVersion === fetchVersionRef.current) {
        setLoading(false);
      }
    }
  }, [activeTab, searchQuery, sortBy, timeRange]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Poll active transcription tasks
  useEffect(() => {
    const activeTasks = Object.values(transcriptionTasks).filter(
      (t) => t.status === "processing" || t.status === "pending"
    );
    if (activeTasks.length === 0) return;
    let active = true;
    let polling = false;
    const interval = setInterval(async () => {
      if (polling) return;
      polling = true;
      for (const task of activeTasks) {
        try {
          const status = await getTranscriptionStatus(task.taskId);
          if (!active) break;
          const updatedTask = {
            ...task,
            status: status.status,
            progress: status.progress || 0,
            stage: status.stage,
            result: status.result,
            error: status.error,
            errorCategory: status.error_category,
            errorDetail: status.error_detail,
            estimate: status.estimate,
            elapsedSeconds: status.elapsed_seconds,
            remainingSeconds: status.remaining_seconds,
          };

          setTranscriptionTasks((prev) => ({
            ...prev,
            [task.fileId]: updatedTask,
          }));

          // Persist updated state
          updateTranscriptionTask(task.fileId, updatedTask);

          // Refresh file list when transcription completes
          if (status.status === "completed" || status.status === "failed") {
            fetchFiles();
          }
        } catch (err) {
          if (!active) break;
          if (err instanceof ApiError && err.status === 404) {
            const failed = {...task, status: "failed", error: "任务已过期，请重新转录", errorCategory: "task_expired"};
            setTranscriptionTasks((prev) => ({...prev, [task.fileId]: failed}));
            updateTranscriptionTask(task.fileId, failed);
          } else { setError("暂时无法获取转录状态，连接恢复后将自动重试"); }
        }
      }
      polling = false;
    }, 2000);

    return () => { active = false; clearInterval(interval); };
  }, [transcriptionTasks, fetchFiles]);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("zh-CN", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getErrorMessage = (error: string, category: string | null, errorDetail?: string | null): string => {
    // If we have detailed error info, show it
    if (errorDetail && errorDetail.length > 10) {
      return errorDetail;
    }
    
    switch (category) {
      case "file_not_found":
        return "音频文件不存在或已被删除";
      case "file_too_large":
        return "音频文件过大，请尝试压缩或分段处理";
      case "invalid_format":
      case "unsupported_format":
        return "不支持的音频格式，请使用 MP3、WAV、M4A 格式";
      case "model_load_error":
      case "model_load_failed":
        return "转录模型加载失败，请检查模型文件是否完整";
      case "model_not_installed":
        return "转录模型未安装，请联系管理员配置";
      case "out_of_memory":
        return "内存不足，无法完成转录";
      case "language_not_supported":
        return "该音频语言暂不支持，目前支持中文和英文";
      case "timeout":
        return "转录超时，请稍后重试或检查音频质量";
      case "network_error":
        return "网络连接异常，请检查网络后重试";
      case "server_busy":
        return "服务器繁忙，请稍后重试";
      default:
        return error || "转录失败，请重试";
    }
  };

  const getErrorSuggestion = (category: string | null): string => {
    switch (category) {
      case "file_not_found":
        return "请重新下载音频文件或检查文件路径";
      case "file_too_large":
        return "建议使用音频编辑工具压缩文件，或分段转录";
      case "invalid_format":
      case "unsupported_format":
        return "可使用格式工厂等工具转换音频格式";
      case "model_load_error":
      case "model_load_failed":
        return "请联系管理员检查模型配置";
      case "model_not_installed":
        return "请运行: pip install openai-whisper 或联系管理员配置模型";
      case "out_of_memory":
        return "尝试转录较短的音频片段，或等待系统资源释放";
      case "language_not_supported":
        return "目前仅支持中文和英文播客转录";
      case "timeout":
        return "建议将音频分割为 10-15 分钟片段分别转录";
      case "network_error":
        return "请检查网络连接，确保能访问后端服务";
      case "server_busy":
        return "请等待几分钟后重试";
      default:
        return "如果问题持续存在，请联系技术支持";
    }
  };

  const handleDeleteFile = async (file: LibraryFile) => {
    if (deletingId === file.id) return;
    if (!confirm(`确定删除「${file.name}」吗？此操作不可恢复。`)) return;
    setDeletingId(file.id);
    try {
      await deleteLibraryFile(file.file_path);
      await fetchFiles();
    } catch (err: any) {
      alert(`删除失败: ${err.message || "未知错误"}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleOpenLocation = async (file: LibraryFile) => {
    setOpeningId(file.id);
    try {
      const res = await openLibraryLocation(file.file_path);
      if (!res.success) alert(res.message);
    } catch (err: any) {
      alert(`打开失败: ${err.message || "未知错误"}`);
    } finally {
      setOpeningId(null);
    }
  };

  const handleTranscribe = async (file: LibraryFile) => {
    if (transcribingId === file.id) return;
    setTranscribingId(file.id);

    try {
      const response = await startTranscriptionByPath(file.file_path);

      const newTask: TranscriptionTask = {
        fileId: file.id,
        taskId: response.task_id,
        status: "processing",
        progress: 0,
        result: null,
        error: null,
        errorCategory: null,
        estimate: response.estimate,
        elapsedSeconds: null,
        remainingSeconds: response.estimate?.total_seconds ?? null,
      };

      setTranscriptionTasks((prev) => ({
        ...prev,
        [file.id]: newTask,
      }));

      // Persist to localStorage
      saveTranscriptionTask(newTask);
    } catch (err: any) {
      const errorMsg = err.message || "未知错误";
      const errorCategory = err.status === 404 ? "file_not_found" : 
                           err.status === 413 ? "file_too_large" :
                           err.status === 415 ? "unsupported_format" :
                           err.status === 503 ? "server_busy" :
                           err.status === 504 ? "timeout" : null;

      // Create failed task for persistence
      const failedTask: TranscriptionTask = {
        fileId: file.id,
        taskId: `failed_${Date.now()}`,
        status: "failed",
        progress: 0,
        result: null,
        error: getErrorMessage(errorMsg, errorCategory),
        errorCategory,
        estimate: null,
        elapsedSeconds: null,
        remainingSeconds: null,
      };

      setTranscriptionTasks((prev) => ({
        ...prev,
        [file.id]: failedTask,
      }));
      saveTranscriptionTask(failedTask);
    } finally {
      setTranscribingId(null);
    }
  };

  const autoTranscribeHandledRef = useRef(false);

  /* 支持 ?transcribe_path=xxx 参数：从下载完成通知跳转后自动触发转录 */
  useEffect(() => {
    if (autoTranscribeHandledRef.current) return;
    const transcribePath = new URLSearchParams(window.location.search).get("transcribe_path");
    if (!transcribePath) return;
    if (loading) return;
    autoTranscribeHandledRef.current = true;
    window.history.replaceState({}, "", window.location.pathname);

    const targetFile = files.find((f) => f.file_path === transcribePath);
    if (targetFile) {
      handleTranscribe(targetFile);
    } else {
      alert("未在文件库中找到该音频文件，请刷新文件库后手动点击对应文件的转录按钮。");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, loading]);

  const handleRetryTranscription = async (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    if (!file) return;
    handleTranscribe(file);
  };

  const handleUseTranscript = (task: TranscriptionTask) => {
    if (!task.result?.text) return;
    // Navigate to create page with transcript text
    window.location.href = `/dashboard/create?transcript_task=${encodeURIComponent(task.taskId)}`;
  };

  const handleViewTranscript = (task: TranscriptionTask) => {
    setViewerTask(task);
    setViewerOpen(true);
  };

  const handleViewTranscriptFile = (file: LibraryFile) => {
    setViewerTask({
      fileId: file.id,
      taskId: `file_${file.id}`,
      status: "completed",
      progress: 100,
      result: null,
      error: null,
      errorCategory: null,
      estimate: null,
      elapsedSeconds: null,
      remainingSeconds: null,
    });
    setViewerOpen(true);
  };

  const handleCloseViewer = () => {
    setViewerOpen(false);
    setViewerTask(null);
  };

  const getTranscriptionTask = (fileId: string): TranscriptionTask | undefined => {
    return transcriptionTasks[fileId];
  };

  return (
    <div className="max-w-5xl mx-auto">
      <DevBanner />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
          File Library
        </p>

        {/* Stats */}
        <div className="mb-4 flex justify-end">
          <input ref={uploadRef} type="file" accept=".mp3,.m4a,.aac,.ogg,.wav,.flac,.wma,.opus" aria-label="选择音频文件" className="hidden" onChange={(event) => void handleUpload(event.target.files?.[0])} />
          <button disabled={uploading} onClick={() => uploadRef.current?.click()} className="rounded-full bg-white px-4 py-2 text-xs font-semibold text-black disabled:opacity-50">{uploading ? "上传中..." : "上传音频"}</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`bg-[#0c0c0e]/70 border rounded-2xl p-4 backdrop-blur-md text-left transition ${
                activeTab === tab.key
                  ? "border-gray-600"
                  : "border-gray-900 hover:border-gray-800"
              }`}
            >
              <div className="flex items-center justify-between">
                <tab.icon className={`w-4 h-4 ${activeTab === tab.key ? "text-white" : "text-gray-600"}`} />
                <span className={`text-xl font-bold ${activeTab === tab.key ? "text-white" : "text-gray-500"}`}>
                  {tab.key === "all"
                    ? (typeCounts.audio || 0) + (typeCounts.transcript || 0) + (typeCounts.image || 0)
                    : typeCounts[tab.key] || 0}
                </span>
              </div>
              <div className={`text-xs mt-1 ${activeTab === tab.key ? "text-gray-400" : "text-gray-600"}`}>
                {tab.label}
              </div>
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-3 mb-6">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文件名、播客名称..."
              className="w-full bg-[#0c0c0e]/70 border border-gray-900 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-700 focus:outline-none focus:border-gray-700 transition"
            />
          </div>

          {/* Sort */}
          <div className="relative">
            <ArrowUpDown className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-[#0c0c0e]/70 border border-gray-900 rounded-xl pl-10 pr-8 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-gray-700 transition appearance-none cursor-pointer"
            >
              {sortOptions.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Time Range */}
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="bg-[#0c0c0e]/70 border border-gray-900 rounded-xl pl-10 pr-8 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-gray-700 transition appearance-none cursor-pointer"
            >
              {timeRanges.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl mb-4"
            >
              <AlertCircle className="w-4 h-4 text-red-400" />
              <p className="text-xs text-red-400">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* File List */}
        <div className="space-y-2">
          <AnimatePresence mode="wait">
            {loading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="text-center py-16"
              >
                <Loader2 className="w-8 h-8 text-gray-700 mx-auto mb-3 animate-spin" />
                <p className="text-sm text-gray-600">加载中...</p>
              </motion.div>
            ) : files.length > 0 ? (
              <motion.div
                key="file-list"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-2"
              >
                {files.map((file, index) => {
                  const config = typeConfig[file.type] || typeConfig.audio;
                  const TypeIcon = config.icon;
                  const task = getTranscriptionTask(file.id);
                  const isAudio = file.type === "audio";

                  return (
                    <motion.div
                      key={file.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.3 }}
                      className="bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-4 backdrop-blur-md hover:border-gray-800 transition group"
                    >
                      <div className="flex flex-wrap items-center gap-4 sm:flex-nowrap">
                        <div className={`w-10 h-10 rounded-xl ${config.bg} flex items-center justify-center flex-shrink-0`}>
                          <TypeIcon className={`w-5 h-5 ${config.color}`} />
                        </div>

                        <div className="min-w-0 flex-1 basis-[calc(100%-56px)] sm:basis-0">
                          <h3 className="text-sm font-medium text-white truncate">
                            {file.episode_title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-gray-600">
                            <span>{file.podcast_name}</span>
                            <span className="flex items-center gap-1">
                              <HardDrive className="w-3 h-3" />
                              {file.size_mb} MB
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDate(file.created_at)}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition">
                          {/* Transcribe button for audio files */}
                          {isAudio && !task && (
                            <button
                              onClick={() => handleTranscribe(file)}
                              disabled={transcribingId === file.id}
                              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 transition disabled:opacity-50"
                              title="转录"
                            >
                              {transcribingId === file.id ? (
                                <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin" />
                              ) : (
                                <Mic className="w-3.5 h-3.5 text-emerald-400" />
                              )}
                              <span className="text-xs text-emerald-400">转录</span>
                            </button>
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

                          <button
                            onClick={() => handleOpenLocation(file)}
                            disabled={openingId === file.id}
                            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition disabled:opacity-50"
                            title="打开位置"
                          >
                            {openingId === file.id ? (
                              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                            ) : (
                              <ExternalLink className="w-4 h-4 text-gray-400" />
                            )}
                          </button>
                          <button
                            className="p-2 rounded-xl bg-white/5 hover:bg-red-500/10 transition"
                            title="删除"
                            onClick={() => handleDeleteFile(file)}
                            disabled={deletingId === file.id}
                          >
                            {deletingId === file.id ? (
                              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Transcription progress / result */}
                      {task && (
                        <div
                          className="mt-3 pt-3 border-t border-white/[0.04] cursor-pointer"
                          onClick={() =>
                            setExpandedTaskId(expandedTaskId === file.id ? null : file.id)
                          }
                        >
                          {/* Use TranscriptionProgress component for processing states */}
                          {task.status === "processing" || task.status === "pending" ? (
                            <TranscriptionProgress
                              progress={task.progress}
                              status={task.status}
                              stage={task.stage}
                              estimate={task.estimate}
                              elapsedSeconds={task.elapsedSeconds}
                              remainingSeconds={task.remainingSeconds}
                            />
                          ) : (
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                {task.status === "completed" ? (
                                  <>
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                    <span className="text-xs text-emerald-400">
                                      转录完成
                                      {task.result && (
                                        <span className="text-gray-500 ml-1">
                                          {task.result.word_count} 字 · {task.result.language}
                                        </span>
                                      )}
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <XCircle className="w-3.5 h-3.5 text-red-400" />
                                    <span className="text-xs text-red-400">
                                      {getErrorMessage(task.error || "", task.errorCategory, task.errorDetail)}
                                    </span>
                                  </>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                {task.status === "completed" && task.result && (
                                  <>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleViewTranscript(task);
                                      }}
                                      className="text-xs text-blue-400 hover:text-blue-300 transition"
                                    >
                                      查看文本
                                    </button>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleUseTranscript(task);
                                      }}
                                      className="text-xs text-emerald-400 hover:text-emerald-300 transition"
                                    >
                                      生成笔记 →
                                    </button>
                                  </>
                                )}
                                {task.status === "failed" && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRetryTranscription(file.id);
                                    }}
                                    className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition"
                                  >
                                    <RotateCcw className="w-3 h-3" />
                                    重试
                                  </button>
                                )}
                                <motion.div
                                  animate={{
                                    rotate: expandedTaskId === file.id ? 180 : 0,
                                  }}
                                  transition={{ duration: 0.2 }}
                                >
                                  <ChevronDown className="w-3 h-3 text-gray-600" />
                                </motion.div>
                              </div>
                            </div>
                          )}

                          {/* Error details for failed tasks */}
                          {task.status === "failed" && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              transition={{ duration: 0.2 }}
                              className="mt-2 overflow-hidden"
                            >
                              <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl">
                                <p className="text-[10px] text-gray-500 mb-1">解决方案</p>
                                <p className="text-xs text-gray-400">
                                  {getErrorSuggestion(task.errorCategory)}
                                </p>
                              </div>
                            </motion.div>
                          )}

                          {/* Expanded details */}
                          {expandedTaskId === file.id && task.result && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              transition={{ duration: 0.2 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-2 pt-2 border-t border-white/[0.04]">
                                <div className="flex items-center justify-between mb-1">
                                  <p className="text-[10px] text-gray-500">转录文本预览</p>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleViewTranscript(task);
                                    }}
                                    className="text-[10px] text-emerald-400 hover:text-emerald-300 transition"
                                  >
                                    查看完整文本 →
                                  </button>
                                </div>
                                <p className="text-xs text-gray-400 line-clamp-3">
                                  {task.result.text}
                                </p>
                                <div className="flex items-center gap-3 mt-2">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleViewTranscript(task);
                                    }}
                                    className="text-xs text-emerald-400 hover:text-emerald-300 transition"
                                  >
                                    查看完整文本
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleUseTranscript(task);
                                    }}
                                    className="text-xs text-gray-500 hover:text-gray-400 transition"
                                  >
                                    生成笔记 →
                                  </button>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="text-center py-16"
              >
                <FolderOpen className="w-12 h-12 text-gray-800 mx-auto mb-4" />
                <p className="text-sm text-gray-600 mb-1">
                  {activeTab === "all"
                    ? "暂无文件"
                    : `暂无${tabs.find((t) => t.key === activeTab)?.label}文件`}
                </p>
                <p className="text-xs text-gray-700">
                  {activeTab === "audio" || activeTab === "all"
                    ? "前往播客搜索下载音频"
                    : activeTab === "transcript"
                    ? "上传音频文件开始转录"
                    : "前往内容创作生成图片"}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Transcript Viewer Modal */}
      <TranscriptViewer
        isOpen={viewerOpen}
        onClose={handleCloseViewer}
        title={files.find(f => f.id === viewerTask?.fileId)?.episode_title || "转录文本"}
        text={viewerTask?.result?.text || ""}
        fileId={viewerTask?.taskId.startsWith("file_") ? viewerTask.taskId.slice(5) : viewerTask?.fileId}
        metadata={viewerTask?.result ? {
          word_count: viewerTask.result.word_count,
          language: viewerTask.result.language || undefined,
          engine_used: viewerTask.result.engine_used || undefined,
          duration_seconds: viewerTask.result.duration_seconds || undefined,
        } : null}
      />
    </div>
  );
}
