"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download,
  Loader2,
  CheckCircle2,
  XCircle,
  RotateCcw,
  FolderOpen,
  X,
  WifiOff,
  HardDrive,
  Lock,
  Rss,
  Info,
  ChevronDown,
} from "lucide-react";
import { DownloadStatusResponse, openDownloadFolder } from "@/lib/api";

export interface DownloadTask {
  taskId: string;
  podcastTitle: string;
  episodeTitle?: string;
  status: string;
  progress: number;
  error?: string;
  errorCategory?: string;
  result?: DownloadStatusResponse["result"];
  // Enhanced progress info
  downloadedBytes?: number;
  totalBytes?: number;
  speed?: string;
  eta?: string;
}

interface DownloadManagerProps {
  tasks: DownloadTask[];
  onClose: () => void;
  onRetry: (taskId: string) => void;
  onRemove: (taskId: string) => void;
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

function getErrorAction(category?: string): string {
  switch (category) {
    case "network_error":
      return "请检查网络连接后重试";
    case "storage_error":
      return "请清理磁盘空间后重试";
    case "permission_error":
      return "请检查文件夹权限后重试";
    case "rss_parse_error":
      return "RSS 源可能已失效，请尝试其他播客";
    case "timeout_error":
      return "下载超时，请稍后重试";
    default:
      return "请重试或联系支持";
  }
}

export default function DownloadManager({ tasks, onClose, onRetry, onRemove }: DownloadManagerProps) {
  const processingCount = tasks.filter((t) => t.status === "processing").length;
  const completedCount = tasks.filter((t) => t.status === "completed").length;
  const [openingTaskId, setOpeningTaskId] = useState<string | null>(null);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, x: 300 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 300 }}
      transition={{ type: "spring", damping: 25, stiffness: 200 }}
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
        <div className="flex items-center gap-2">
          {processingCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-amber-400">
              <Loader2 className="w-3 h-3 animate-spin" />
              {processingCount} 个下载中
            </span>
          )}
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {tasks.length === 0 ? (
          <div className="text-center py-12">
            <Download className="w-8 h-8 text-gray-700 mx-auto mb-3" />
            <p className="text-xs text-gray-600">暂无下载任务</p>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {tasks.map((task) => (
              <motion.div
                key={task.taskId}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 100 }}
                className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 cursor-pointer hover:border-white/[0.08] transition"
                onClick={() => setExpandedTaskId(expandedTaskId === task.taskId ? null : task.taskId)}
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center flex-shrink-0">
                    {task.status === "completed" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : task.status === "failed" ? (
                      getErrorIcon(task.errorCategory)
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

                    {/* Progress bar with enhanced info */}
                    {task.status === "processing" && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                          <span>{task.progress.toFixed(1)}%</span>
                          <span className="flex items-center gap-2">
                            {task.speed && <span>{task.speed}</span>}
                            {task.eta && <span>剩余 {task.eta}</span>}
                            {task.totalBytes && task.totalBytes > 0 && task.downloadedBytes ? (
                              <span>{formatBytes(task.downloadedBytes)} / {formatBytes(task.totalBytes)}</span>
                            ) : task.downloadedBytes && task.downloadedBytes > 0 ? (
                              <span>已下载 {formatBytes(task.downloadedBytes)}</span>
                            ) : task.result?.file_size_mb ? (
                              <span>{(task.result.file_size_mb * task.progress / 100).toFixed(1)} / {task.result.file_size_mb} MB</span>
                            ) : (
                              "下载中..."
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
                        {task.totalBytes === 0 && task.downloadedBytes && task.downloadedBytes > 0 && (
                          <p className="text-[10px] text-gray-600 mt-1">服务器未提供文件大小，进度为估算值</p>
                        )}
                      </div>
                    )}

                    {/* Completed */}
                    {task.status === "completed" && task.result && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] text-emerald-400">
                          {task.result.file_size_mb} MB
                        </span>
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            if (openingTaskId === task.taskId) return;
                            setOpeningTaskId(task.taskId);
                            try {
                              await openDownloadFolder(task.taskId);
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
                              } else if (status === 500) {
                                alert(`打开文件夹失败，请手动前往: ${task.result?.file_path || "未知路径"}`);
                              } else {
                                alert(`打开文件夹失败: ${msg}`);
                              }
                            } finally {
                              setOpeningTaskId(null);
                            }
                          }}
                          disabled={openingTaskId === task.taskId}
                          className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-white transition disabled:opacity-50"
                        >
                          {openingTaskId === task.taskId ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <FolderOpen className="w-3 h-3" />
                          )}
                          打开位置
                        </button>
                      </div>
                    )}

                    {/* Failed with enhanced error info */}
                    {task.status === "failed" && (
                      <div className="mt-2">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-red-400 truncate max-w-[180px]">
                            {task.error || "下载失败"}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onRetry(task.taskId);
                            }}
                            className="flex items-center gap-1 text-[10px] text-amber-400 hover:text-amber-300 transition"
                          >
                            <RotateCcw className="w-3 h-3" />
                            重试
                          </button>
                        </div>
                        <p className="text-[10px] text-gray-600 mt-0.5">
                          {getErrorAction(task.errorCategory)}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Expand indicator */}
                  <div className="flex flex-col items-center gap-1">
                    <motion.div
                      animate={{ rotate: expandedTaskId === task.taskId ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ChevronDown className="w-3 h-3 text-gray-600" />
                    </motion.div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemove(task.taskId);
                      }}
                      className="p-1 text-gray-600 hover:text-gray-400 transition flex-shrink-0"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* Expanded details */}
                <AnimatePresence>
                  {expandedTaskId === task.taskId && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 pt-2 border-t border-white/[0.04]">
                        <div className="space-y-1">
                          <p className="text-[10px] text-gray-600">
                            <span className="text-gray-500">任务 ID:</span> {task.taskId}
                          </p>
                          {task.result?.file_path && (
                            <p className="text-[10px] text-gray-600">
                              <span className="text-gray-500">文件路径:</span>{" "}
                              <span className="text-gray-400 break-all">{task.result.file_path}</span>
                            </p>
                          )}
                          {task.error && (
                            <p className="text-[10px] text-red-400">
                              <span className="text-gray-500">错误详情:</span> {task.error}
                            </p>
                          )}
                          {task.errorCategory && (
                            <p className="text-[10px] text-gray-600">
                              <span className="text-gray-500">错误类型:</span>{" "}
                              <span className="text-amber-400">{task.errorCategory}</span>
                            </p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Footer summary */}
      {tasks.length > 0 && (
        <div className="p-4 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-gray-600">
          <span>已完成: {completedCount}</span>
          <span>进行中: {processingCount}</span>
          <span>失败: {tasks.filter((t) => t.status === "failed").length}</span>
        </div>
      )}
    </motion.div>
  );
}
