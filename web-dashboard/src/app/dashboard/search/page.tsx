"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Radio,
  ArrowRight,
  Clock,
  User,
  AlertCircle,
  Download,
  Loader2,
  CheckCircle2,
  ListMusic,
  Info,
  X,
} from "lucide-react";
import EpisodeList from "@/components/EpisodeList";
import DownloadManager, { DownloadTask } from "@/components/DownloadManager";
import {
  searchPodcasts,
  PodcastResult,
  startDownload,
  getDownloadStatus,
  retryDownload,
} from "@/lib/api";
import DevBanner from "@/components/DevBanner";

interface Notification {
  id: string;
  type: "success" | "error" | "info";
  message: string;
  taskId?: string;
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PodcastResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);
  const [expandedPodcastId, setExpandedPodcastId] = useState<string | null>(null);
  const [downloadTasks, setDownloadTasks] = useState<DownloadTask[]>([]);
  const [showDownloadManager, setShowDownloadManager] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = (type: "success" | "error" | "info", message: string, taskId?: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setNotifications((prev) => [...prev, { id, type, message, taskId }]);
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 6000);
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    setError("");
    setHasSearched(true);

    try {
      const data = await searchPodcasts(query);
      setResults(data.results);
    } catch (err) {
      setError("搜索失败，请检查后端服务是否运行");
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleDownload = async (podcast: PodcastResult, episodeIndex: number = 0, episodeTitle?: string) => {
    if (!podcast.rss_url) {
      setDownloadError("该播客没有提供 RSS 链接，无法下载");
      addNotification("error", "该播客没有提供 RSS 链接，无法下载");
      return;
    }

    setDownloadingId(podcast.id);
    setDownloadError("");
    setDownloadSuccess(null);

    try {
      const response = await startDownload({
        rss_url: podcast.rss_url,
        episode_index: episodeIndex,
      });

      const newTask: DownloadTask = {
        taskId: response.task_id,
        podcastTitle: podcast.title,
        episodeTitle: episodeTitle || "最新单集",
        status: "processing",
        progress: 0,
      };
      setDownloadTasks((prev) => [newTask, ...prev]);
      addNotification("info", `开始下载: ${episodeTitle || podcast.title}`, response.task_id);

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
                    downloadedBytes: status.downloaded_bytes,
                    totalBytes: status.total_bytes,
                    result: status.result,
                    error: status.error,
                    errorCategory: status.error_category,
                  }
                : task
            )
          );

          if (status.status === "completed") {
            clearInterval(pollInterval);
            setDownloadingId(null);
            setDownloadSuccess(`《${status.result?.episode_title || "未知单集"}》下载完成`);
            addNotification("success", `下载完成: ${status.result?.episode_title || "文件"}`, response.task_id);
            setTimeout(() => setDownloadSuccess(null), 5000);
          } else if (status.status === "failed") {
            clearInterval(pollInterval);
            setDownloadingId(null);
            const errorMsg = status.error || "未知错误";
            addNotification("error", `下载失败: ${errorMsg}`, response.task_id);
          }
        } catch (err) {
          clearInterval(pollInterval);
          setDownloadingId(null);
          addNotification("error", "下载状态获取失败，请查看下载管理器");
        }
      }, 1000);

    } catch (err) {
      setDownloadingId(null);
      const errorMsg = err instanceof Error ? err.message : "下载失败";
      setDownloadError(errorMsg);
      addNotification("error", errorMsg);
    }
  };

  const handleRetry = async (taskId: string) => {
    try {
      await retryDownload(taskId);

      setDownloadTasks((prev) =>
        prev.map((task) =>
          task.taskId === taskId
            ? { ...task, status: "processing", progress: 0, error: undefined, errorCategory: undefined }
            : task
        )
      );
      addNotification("info", "开始重试下载", taskId);

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
                    errorCategory: status.error_category,
                  }
                : task
            )
          );
          if (status.status === "completed") {
            clearInterval(pollInterval);
            addNotification("success", `重试下载完成: ${status.result?.episode_title || "文件"}`, taskId);
          } else if (status.status === "failed") {
            clearInterval(pollInterval);
            addNotification("error", `重试失败: ${status.error || "未知错误"}`, taskId);
          }
        } catch {
          clearInterval(pollInterval);
        }
      }, 1000);
    } catch (err) {
      console.error("Retry failed:", err);
      addNotification("error", "重试失败");
    }
  };

  const handleRemoveTask = (taskId: string) => {
    setDownloadTasks((prev) => prev.filter((task) => task.taskId !== taskId));
  };

  return (
    <div className="max-w-5xl mx-auto">
      <DevBanner />

      {/* Notifications */}
      <div className="fixed bottom-6 right-6 z-50 space-y-2">
        <AnimatePresence>
          {notifications.map((n) => (
            <motion.div
              key={n.id}
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100 }}
              className={`px-4 py-3 rounded-xl border text-sm flex items-center gap-2 shadow-lg max-w-sm ${
                n.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  : n.type === "error"
                  ? "bg-red-500/10 border-red-500/20 text-red-400"
                  : "bg-blue-500/10 border-blue-500/20 text-blue-400"
              }`}
            >
              {n.type === "success" ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : n.type === "error" ? <AlertCircle className="w-4 h-4 flex-shrink-0" /> : <Info className="w-4 h-4 flex-shrink-0" />}
              <span className="text-xs">{n.message}</span>
              <button
                onClick={() => setNotifications((prev) => prev.filter((item) => item.id !== n.id))}
                className="ml-auto p-0.5 text-gray-500 hover:text-white transition flex-shrink-0"
              >
                <X className="w-3 h-3" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Download Manager Panel */}
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

      {/* Search Input */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
          Podcast Search
        </p>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-3.5 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="搜索播客名称、主持人或关键词..."
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/20 transition-all"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={isSearching || !query.trim()}
            className="bg-white text-black px-6 py-3 rounded-xl font-medium text-sm hover:bg-gray-100 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSearching ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full"
              />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            搜索
          </button>
        </div>
      </motion.div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

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

      {/* Download Progress Indicator - Clickable */}
      {downloadTasks.filter((t) => t.status === "processing").length > 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={() => setShowDownloadManager(true)}
          className="fixed right-6 top-6 z-40 flex items-center gap-2 px-4 py-2 bg-white/[0.05] border border-white/[0.08] rounded-xl text-xs text-gray-400 cursor-pointer hover:bg-white/[0.08] transition"
        >
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>{downloadTasks.filter((t) => t.status === "processing").length} 个下载中</span>
        </motion.div>
      )}

      {/* Download Manager Toggle (when no active downloads but has tasks) */}
      {downloadTasks.length > 0 && downloadTasks.filter((t) => t.status === "processing").length === 0 && (
        <motion.button
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={() => setShowDownloadManager(true)}
          className="fixed right-6 top-6 z-40 flex items-center gap-2 px-4 py-2 bg-white/[0.05] border border-white/[0.08] rounded-xl text-xs text-gray-400 cursor-pointer hover:bg-white/[0.08] transition"
        >
          <Download className="w-4 h-4" />
          <span>下载管理 ({downloadTasks.length})</span>
        </motion.button>
      )}

      {/* Results */}
      <AnimatePresence mode="wait">
        {isSearching ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5 animate-pulse"
              >
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 bg-white/5 rounded-xl flex-shrink-0" />
                  <div className="flex-1 space-y-3">
                    <div className="h-4 bg-white/5 rounded w-1/3" />
                    <div className="h-3 bg-white/5 rounded w-1/4" />
                    <div className="h-3 bg-white/5 rounded w-3/4" />
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        ) : results.length > 0 ? (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            <p className="text-xs text-gray-500 mb-4">
              找到 {results.length} 个结果
            </p>
            {results.map((podcast, index) => (
              <motion.div
                key={podcast.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5 hover:border-white/[0.12] transition-all cursor-pointer group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 bg-white/[0.04] rounded-xl flex items-center justify-center flex-shrink-0">
                    <Radio className="w-6 h-6 text-gray-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-white font-medium text-sm mb-1 group-hover:text-gray-200 transition-colors">
                      {podcast.title}
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {podcast.author}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {podcast.episode_count} 集
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2">
                      {podcast.description}
                    </p>
                  </div>
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
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedPodcastId(
                          expandedPodcastId === podcast.id ? null : podcast.id
                        );
                      }}
                      className={`p-2 rounded-xl transition ${
                        expandedPodcastId === podcast.id
                          ? "bg-white/10 text-white"
                          : "bg-white/5 hover:bg-white/10 text-gray-400"
                      }`}
                      title="查看单集列表"
                    >
                      <ListMusic className="w-4 h-4" />
                    </button>
                    <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-white transition-colors" />
                  </div>
                </div>
                <AnimatePresence>
                  {expandedPodcastId === podcast.id && (
                    <EpisodeList
                      rssUrl={podcast.rss_url}
                      podcastTitle={podcast.title}
                      onClose={() => setExpandedPodcastId(null)}
                      onDownload={(idx, title) => handleDownload(podcast, idx, title)}
                    />
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </motion.div>
        ) : hasSearched ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <p className="text-gray-600 text-sm">未找到相关播客</p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
