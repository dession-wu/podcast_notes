"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock,
  Calendar,
  Download,
  Loader2,
  ArrowUpDown,
  Headphones,
  X,
} from "lucide-react";
import { getEpisodes, EpisodeItem, startDownload, getDownloadStatus } from "@/lib/api";

interface EpisodeListProps {
  rssUrl: string;
  podcastTitle: string;
  onClose: () => void;
  onDownload?: (episodeIndex: number, episodeTitle: string) => void;
}

export default function EpisodeList({ rssUrl, podcastTitle, onClose, onDownload }: EpisodeListProps) {
  const [episodes, setEpisodes] = useState<EpisodeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);
  const [totalEpisodes, setTotalEpisodes] = useState(0);
  const [downloadingIndex, setDownloadingIndex] = useState<number | null>(null);
  const [pendingDownloads, setPendingDownloads] = useState<Set<number>>(new Set());
  const pageSize = 20;

  useEffect(() => {
    loadEpisodes();
  }, [rssUrl, sort, page]);

  const loadEpisodes = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getEpisodes({
        rss_url: rssUrl,
        sort,
        page,
        page_size: pageSize,
      });
      setEpisodes(data.episodes);
      setTotalEpisodes(data.total_episodes);
    } catch (err) {
      setError("加载单集列表失败");
      console.error("Load episodes error:", err);
    } finally {
      setLoading(false);
    }
  };

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

    setDownloadingIndex(episode.index);
    try {
      const response = await startDownload({
        rss_url: rssUrl,
        episode_index: episode.index,
      });

      const pollInterval = setInterval(async () => {
        try {
          const status = await getDownloadStatus(response.task_id);
          if (status.status === "completed" || status.status === "failed") {
            clearInterval(pollInterval);
            setDownloadingIndex(null);
          }
        } catch {
          clearInterval(pollInterval);
          setDownloadingIndex(null);
        }
      }, 2000);

      setTimeout(() => {
        clearInterval(pollInterval);
        setDownloadingIndex(null);
      }, 60000);
    } catch (err) {
      setDownloadingIndex(null);
      setError("下载失败");
    }
  };

  const totalPages = Math.ceil(totalEpisodes / pageSize);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-4 border-t border-white/[0.06] pt-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-medium text-white">单集列表</h4>
          <p className="text-xs text-gray-500 mt-0.5">
            共 {totalEpisodes} 集
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setSort(sort === "newest" ? "oldest" : "newest");
              setPage(1);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-400 hover:bg-white/10 transition"
          >
            <ArrowUpDown className="w-3 h-3" />
            {sort === "newest" ? "最新优先" : "最早优先"}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white/[0.02] rounded-xl p-4 animate-pulse">
              <div className="h-3 bg-white/5 rounded w-2/3 mb-2" />
              <div className="h-2 bg-white/5 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : (
        <>
          {/* Episode List */}
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {episodes.map((episode) => (
              <motion.div
                key={episode.index}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.04] rounded-xl p-3.5 transition group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Headphones className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h5 className="text-sm text-white font-medium truncate">
                      {episode.title}
                    </h5>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-500">
                      {episode.duration_formatted && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {episode.duration_formatted}
                        </span>
                      )}
                      {episode.publish_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(episode.publish_date).toLocaleDateString("zh-CN")}
                        </span>
                      )}
                      {episode.episode_number && (
                        <span>第 {episode.episode_number} 期</span>
                      )}
                    </div>
                    {episode.description && (
                      <p className="text-[11px] text-gray-600 mt-1.5 line-clamp-2">
                        {episode.description}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDownload(episode)}
                    disabled={downloadingIndex === episode.index || pendingDownloads.has(episode.index)}
                    className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition disabled:opacity-50 flex-shrink-0"
                    title="下载该单集"
                  >
                    {downloadingIndex === episode.index || pendingDownloads.has(episode.index) ? (
                      <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/[0.04]">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-400 hover:bg-white/10 transition disabled:opacity-30"
              >
                上一页
              </button>
              <span className="text-xs text-gray-500">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-400 hover:bg-white/10 transition disabled:opacity-30"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
