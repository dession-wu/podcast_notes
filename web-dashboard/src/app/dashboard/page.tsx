"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Headphones,
  FileText,
  Image,
  ArrowRight,
  Loader2,
  Download,
  CheckCircle2,
  XCircle,
  RotateCcw,
  FolderOpen,
  ChevronDown,
  WifiOff,
  HardDrive,
  Lock,
  Rss,
  Info,
  X,
} from "lucide-react";
import Link from "next/link";
import DevBanner from "@/components/DevBanner";
import {
  getDownloadHistory,
  getLibraryFiles,
  getDownloadStatus,
  retryDownload,
  openDownloadFolder,
  DownloadHistoryItem,
} from "@/lib/api";

const quickActions = [
  {
    icon: Search,
    label: "搜索播客",
    description: "搜索并下载播客音频",
    href: "/dashboard/search",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    icon: Headphones,
    label: "上传音频",
    description: "上传音频进行转录",
    href: "/dashboard/library",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    icon: FileText,
    label: "生成笔记",
    description: "AI 生成小红书风格笔记",
    href: "/dashboard/create",
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
  {
    icon: Image,
    label: "生成图片",
    description: "生成小红书封面图片",
    href: "/dashboard/create",
    color: "text-purple-400",
    bg: "bg-purple-400/10",
  },
];

interface DashboardStats {
  totalDownloads: number;
  totalTranscriptHours: number;
  totalNotes: number;
  totalImages: number;
  activeDownloads: number;
  completedDownloads: number;
  failedDownloads: number;
}

interface DownloadTask extends DownloadHistoryItem {
  speed?: string;
  eta?: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function getErrorIcon(category?: string) {
  switch (category) {
    case "network_error":
      return <WifiOff className="w-4 h-4 text-red-400" />;
    case "storage_error":
      return <HardDrive className="w-4 h-4 text-red-400" />;
    case "permission_error":
      return <Lock className="w-4 h-4 text-red-400" />;
    case "rss_parse_error":
      return <Rss className="w-4 h-4 text-red-400" />;
    default:
      return <XCircle className="w-4 h-4 text-red-400" />;
  }
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalDownloads: 0,
    totalTranscriptHours: 0,
    totalNotes: 0,
    totalImages: 0,
    activeDownloads: 0,
    completedDownloads: 0,
    failedDownloads: 0,
  });
  const [loading, setLoading] = useState(true);
  const [downloadTasks, setDownloadTasks] = useState<DownloadTask[]>([]);
  const [showAllTasks, setShowAllTasks] = useState(false);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [openingTaskId, setOpeningTaskId] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch download history
      const historyRes = await getDownloadHistory(50);
      const history = historyRes.history || [];

      // Fetch library files for counts
      const libraryRes = await getLibraryFiles("all", "", "time_desc", "all");
      const files = libraryRes.files || [];
      const typeCounts = libraryRes.type_counts || {};

      const activeCount = history.filter((h) => h.status === "processing").length;
      const completedCount = history.filter((h) => h.status === "completed").length;
      const failedCount = history.filter((h) => h.status === "failed").length;

      // Calculate transcript hours from transcript files
      // Each transcript file represents one transcribed audio
      const transcriptFiles = files.filter((f) => f.type === "transcript");
      const transcriptCount = transcriptFiles.length;

      // Estimate total audio duration from transcript file sizes
      // Rough estimate: 1KB of transcript ≈ 1 minute of audio
      const totalTranscriptKB = transcriptFiles.reduce(
        (sum, f) => sum + (f.size_mb || 0) * 1024,
        0
      );
      const transcriptHours = Math.round((totalTranscriptKB / 60) * 10) / 10;

      setStats({
        totalDownloads: history.length,
        totalTranscriptHours: transcriptHours,
        totalNotes: transcriptCount,
        totalImages: typeCounts["image"] || 0,
        activeDownloads: activeCount,
        completedDownloads: completedCount,
        failedDownloads: failedCount,
      });

      // Update download tasks for display
      setDownloadTasks(history.map((h) => ({ ...h, taskId: h.task_id })));
    } catch (err: any) {
      console.error("Failed to fetch dashboard data:", err);
      // Set empty state on error to prevent infinite loading
      setStats({
        totalDownloads: 0,
        totalTranscriptHours: 0,
        totalNotes: 0,
        totalImages: 0,
        activeDownloads: 0,
        completedDownloads: 0,
        failedDownloads: 0,
      });
      setDownloadTasks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll for active download updates
  const pollActiveDownloads = useCallback(async () => {
    const activeTasks = downloadTasks.filter((t) => t.status === "processing");
    if (activeTasks.length === 0) return;

    const updatedTasks = [...downloadTasks];
    let hasChanges = false;

    for (const task of activeTasks) {
      try {
        const status = await getDownloadStatus(task.task_id);
        const idx = updatedTasks.findIndex((t) => t.task_id === task.task_id);
        if (idx !== -1) {
          updatedTasks[idx] = {
            ...updatedTasks[idx],
            status: status.status,
            progress: status.progress || 0,
          };
          hasChanges = true;
        }
      } catch (err) {
        console.error(`Failed to poll task ${task.task_id}:`, err);
      }
    }

    if (hasChanges) {
      setDownloadTasks(updatedTasks);
      // Refresh stats if any task completed or failed
      const hasCompleted = activeTasks.some(
        (t) => updatedTasks.find((ut) => ut.task_id === t.task_id)?.status !== "processing"
      );
      if (hasCompleted) {
        fetchDashboardData();
      }
    }
  }, [downloadTasks, fetchDashboardData]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Poll every 2 seconds for active downloads
  useEffect(() => {
    const interval = setInterval(() => {
      pollActiveDownloads();
    }, 2000);
    return () => clearInterval(interval);
  }, [pollActiveDownloads]);

  const handleRetry = async (taskId: string) => {
    try {
      await retryDownload(taskId);
      setDownloadTasks((prev) =>
        prev.map((task) =>
          task.task_id === taskId
            ? { ...task, status: "processing", progress: 0, error: undefined, error_category: undefined }
            : task
        )
      );

      // Poll for retry status
      const pollInterval = setInterval(async () => {
        try {
          const status = await getDownloadStatus(taskId);
          setDownloadTasks((prev) =>
            prev.map((task) =>
              task.task_id === taskId
                ? {
                    ...task,
                    status: status.status,
                    progress: status.progress || 0,
                  }
                : task
            )
          );
          if (status.status === "completed" || status.status === "failed") {
            clearInterval(pollInterval);
            fetchDashboardData();
          }
        } catch {
          clearInterval(pollInterval);
        }
      }, 1000);
    } catch (err) {
      console.error("Retry failed:", err);
    }
  };

  const handleOpenFolder = async (taskId: string) => {
    if (openingTaskId === taskId) return;
    setOpeningTaskId(taskId);
    try {
      await openDownloadFolder(taskId);
    } catch (err: any) {
      const status = err?.status;
      const msg = err?.message || "";
      if (status === 404) {
        if (msg.includes("任务不存在")) {
          alert("下载任务不存在");
        } else {
          alert("文件已被移动或删除，请重新下载");
        }
      } else if (status === 400) {
        alert("文件尚未下载完成");
      } else if (status === 403) {
        alert("权限不足，请检查文件夹访问权限");
      } else {
        alert(`打开文件夹失败: ${msg}`);
      }
    } finally {
      setOpeningTaskId(null);
    }
  };

  const displayedTasks = showAllTasks ? downloadTasks : downloadTasks.slice(0, 5);
  const hasMoreTasks = downloadTasks.length > 5;

  const statCards = [
    {
      label: "累计下载",
      value: stats.totalDownloads.toString(),
      suffix: "个音频",
      active: stats.activeDownloads > 0,
      activeText: `${stats.activeDownloads} 个下载中`,
    },
    {
      label: "转录音频",
      value: stats.totalTranscriptHours > 0 ? stats.totalTranscriptHours.toString() : "0",
      suffix: "小时",
    },
    {
      label: "生成笔记",
      value: stats.totalNotes.toString(),
      suffix: "篇",
    },
    {
      label: "生成图片",
      value: stats.totalImages.toString(),
      suffix: "张",
    },
  ];

  return (
    <div className="max-w-5xl mx-auto">
      <DevBanner />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
          Overview
        </p>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-gray-700 mx-auto mb-3 animate-spin" />
              <p className="text-sm text-gray-600">加载中...</p>
            </div>
          </div>
        )}

        {/* Stats */}
        {!loading && (
        <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {statCards.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1, duration: 0.4 }}
              className="bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-5 backdrop-blur-md"
            >
              <p className="text-2xl font-bold text-white mb-1">{stat.value}</p>
              <p className="text-[10px] text-gray-600">{stat.label}</p>
              {stat.active && (
                <p className="text-[10px] text-amber-400 mt-1 flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {stat.activeText}
                </p>
              )}
            </motion.div>
          ))}
        </div>

        {/* Download Status Section */}
        {downloadTasks.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-5 backdrop-blur-md mb-8"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-medium text-white">下载状态</h3>
                <span className="text-xs text-gray-500">({downloadTasks.length})</span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-gray-500">
                <span className="flex items-center gap-1">
                  <Loader2 className="w-3 h-3 text-amber-400 animate-spin" />
                  进行中: {stats.activeDownloads}
                </span>
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  已完成: {stats.completedDownloads}
                </span>
                {stats.failedDownloads > 0 && (
                  <span className="flex items-center gap-1">
                    <XCircle className="w-3 h-3 text-red-400" />
                    失败: {stats.failedDownloads}
                  </span>
                )}
              </div>
            </div>

            <div className="space-y-3">
              {displayedTasks.map((task) => (
                <div
                  key={task.task_id}
                  className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 cursor-pointer hover:border-white/[0.08] transition"
                  onClick={() =>
                    setExpandedTaskId(expandedTaskId === task.task_id ? null : task.task_id)
                  }
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center flex-shrink-0">
                      {task.status === "completed" ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : task.status === "failed" ? (
                        getErrorIcon(task.error_category)
                      ) : (
                        <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-white font-medium truncate">
                        {task.episode_title || "下载任务"}
                      </p>
                      <p className="text-[10px] text-gray-600 truncate">
                        {task.podcast_name}
                      </p>

                      {/* Progress bar */}
                      {task.status === "processing" && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                            <span>{(task.progress || 0).toFixed(1)}%</span>
                            <span>下载中...</span>
                          </div>
                          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                            <motion.div
                              className="h-full bg-emerald-500 rounded-full"
                              initial={{ width: 0 }}
                              animate={{ width: `${task.progress || 0}%` }}
                              transition={{ duration: 0.3 }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Completed */}
                      {task.status === "completed" && (
                        <div className="mt-2 flex items-center gap-2">
                          <span className="text-[10px] text-emerald-400">
                            {task.file_size_mb} MB
                          </span>
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              await handleOpenFolder(task.task_id);
                            }}
                            disabled={openingTaskId === task.task_id}
                            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-white transition disabled:opacity-50"
                          >
                            {openingTaskId === task.task_id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <FolderOpen className="w-3 h-3" />
                            )}
                            打开位置
                          </button>
                        </div>
                      )}

                      {/* Failed */}
                      {task.status === "failed" && (
                        <div className="mt-2">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-red-400 truncate max-w-[180px]">
                              {task.error || "下载失败"}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRetry(task.task_id);
                              }}
                              className="flex items-center gap-1 text-[10px] text-amber-400 hover:text-amber-300 transition"
                            >
                              <RotateCcw className="w-3 h-3" />
                              重试
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col items-center gap-1">
                      <motion.div
                        animate={{
                          rotate: expandedTaskId === task.task_id ? 180 : 0,
                        }}
                        transition={{ duration: 0.2 }}
                      >
                        <ChevronDown className="w-3 h-3 text-gray-600" />
                      </motion.div>
                    </div>
                  </div>

                  {/* Expanded details */}
                  {expandedTaskId === task.task_id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 pt-2 border-t border-white/[0.04]">
                        <div className="space-y-1">
                          <p className="text-[10px] text-gray-600">
                            <span className="text-gray-500">任务 ID:</span>{" "}
                            {task.task_id}
                          </p>
                          {task.error && (
                            <p className="text-[10px] text-red-400">
                              <span className="text-gray-500">错误详情:</span>{" "}
                              {task.error}
                            </p>
                          )}
                          {task.error_category && (
                            <p className="text-[10px] text-gray-600">
                              <span className="text-gray-500">错误类型:</span>{" "}
                              <span className="text-amber-400">
                                {task.error_category}
                              </span>
                            </p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              ))}
            </div>

            {hasMoreTasks && (
              <button
                onClick={() => setShowAllTasks(!showAllTasks)}
                className="w-full mt-3 py-2 text-[10px] text-gray-500 hover:text-white transition border border-white/[0.04] rounded-xl hover:border-white/[0.08]"
              >
                {showAllTasks
                  ? "收起"
                  : `查看全部 ${downloadTasks.length} 个任务`}
              </button>
            )}
          </motion.div>
        )}

        {/* Quick Actions */}
        <div className="mb-8">
          <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
            Quick Actions
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map((action, index) => (
              <motion.div
                key={action.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.1, duration: 0.4 }}
              >
                <Link
                  href={action.href}
                  className="block bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-5 backdrop-blur-md hover:border-gray-700 transition group"
                >
                  <div
                    className={`w-10 h-10 rounded-xl ${action.bg} flex items-center justify-center mb-3`}
                  >
                    <action.icon className={`w-5 h-5 ${action.color}`} />
                  </div>
                  <h3 className="text-sm font-medium text-white mb-1">
                    {action.label}
                  </h3>
                  <p className="text-xs text-gray-600 mb-3">
                    {action.description}
                  </p>
                  <div className="flex items-center gap-1 text-[10px] text-gray-500 group-hover:text-white transition">
                    <span>前往</span>
                    <ArrowRight className="w-3 h-3" />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Tips */}
        {!loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-5 backdrop-blur-md"
        >
          <p className="text-xs text-gray-500 mb-2">使用提示</p>
          <div className="space-y-2 text-xs text-gray-600">
            <p>1. 在「播客搜索」中搜索并下载感兴趣的播客音频</p>
            <p>2. 在「文件库」中管理所有下载和转录的文件</p>
            <p>3. 在「内容创作」中使用 AI 生成小红书风格笔记和图片</p>
          </div>
        </motion.div>
        )}
        </>
        )}
      </motion.div>
    </div>
  );
}
