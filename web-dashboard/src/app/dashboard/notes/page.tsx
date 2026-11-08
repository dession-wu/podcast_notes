"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  NotebookPen,
  ArrowLeft,
  Trash2,
  Download,
  Loader2,
  AlertCircle,
  FileText,
  Clock,
  Tag,
  BookOpen,
  ImageIcon,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import DevBanner from "@/components/DevBanner";
import {
  listNotes,
  getNote,
  deleteNote,
  downloadNoteExport,
  getNoteImages,
  generateNoteImages,
  NoteSummary,
  NoteDetail,
  NoteImage,
} from "@/lib/api";

const PAGE_SIZE = 50;

export default function NotesPage() {
  const [notes, setNotes] = useState<NoteSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [exportingId, setExportingId] = useState<number | null>(null);

  /* 详情视图状态：非空时展示笔记详情 */
  const [detail, setDetail] = useState<NoteDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  /* 详情配图状态：关联图片列表 + 生成/加载状态 */
  const [noteImages, setNoteImages] = useState<NoteImage[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [imageGenerating, setImageGenerating] = useState(false);
  const [imageError, setImageError] = useState("");
  /* 生成服务不可用（503，如 Playwright/Chromium 缺失）时禁用入口 */
  const [imageGenUnavailable, setImageGenUnavailable] = useState(false);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const fetchNotes = useCallback(async (offset = 0, append = false) => {
    setLoading(true);
    setError("");
    try {
      const res = await listNotes(PAGE_SIZE, offset);
      setNotes((prev) => (append ? [...prev, ...res.items] : res.items));
      setTotal(res.total);
      setHasMore(offset + res.items.length < res.total);
    } catch (err: any) {
      setError(err.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotes(0, false);
  }, [fetchNotes]);

  /* 打开详情 */
  const handleOpenNote = async (noteId: number) => {
    setDetailLoading(true);
    setError("");
    /* 重置配图状态并并行加载关联图片 */
    setNoteImages([]);
    setImageError("");
    setImageGenUnavailable(false);
    setImagesLoading(true);
    try {
      const res = await getNote(noteId);
      setDetail(res.note);
    } catch (err: any) {
      setError(err.message || "加载笔记详情失败");
    } finally {
      setDetailLoading(false);
    }
    try {
      const imgRes = await getNoteImages(noteId);
      setNoteImages(imgRes.images);
    } catch {
      /* 图片列表加载失败不阻断详情展示，仅置空 */
      setNoteImages([]);
    } finally {
      setImagesLoading(false);
    }
  };

  /* 关闭详情并刷新列表（删除可能已改变列表） */
  const handleCloseDetail = (refresh = false) => {
    setDetail(null);
    setNoteImages([]);
    setImageError("");
    setImageGenUnavailable(false);
    if (refresh) {
      fetchNotes(0, false);
    }
  };

  /* 为当前笔记生成配图（同步生成，可能耗时较长） */
  const handleGenerateImages = async (noteId: number) => {
    if (imageGenerating || imageGenUnavailable || !detail) return;
    setImageGenerating(true);
    setImageError("");
    try {
      const res = await generateNoteImages(noteId);
      /* 后端返回该笔记的全量配图列表，直接替换，避免追加导致重复 */
      setNoteImages(res.images);
    } catch (err: any) {
      const message = err.message || "配图生成失败";
      setImageError(message);
      /* 生成服务不可用（503）时禁用入口，避免反复失败 */
      if (/unavailable|Playwright|503/i.test(message)) {
        setImageGenUnavailable(true);
      }
    } finally {
      setImageGenerating(false);
    }
  };

  /* 图片新窗口查看大图 */
  const handleOpenImage = (image: NoteImage) => {
    window.open(`/images/${encodeURIComponent(image.image_name)}`, "_blank");
  };

  /* 下载图片 */
  const handleDownloadImage = (image: NoteImage) => {
    const a = document.createElement("a");
    a.href = `/images/${encodeURIComponent(image.image_name)}`;
    a.download = image.image_name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  /* 删除笔记（confirm 模式，与文件库一致） */
  const handleDeleteNote = async (note: NoteSummary | NoteDetail) => {
    if (deletingId === note.id) return;
    if (!confirm(`确定删除笔记「${note.title}」吗？此操作不可恢复。`)) return;
    setDeletingId(note.id);
    try {
      await deleteNote(note.id);
      if (detail && detail.id === note.id) {
        handleCloseDetail(true);
      } else {
        fetchNotes(0, false);
      }
    } catch (err: any) {
      alert(`删除失败: ${err.message || "未知错误"}`);
    } finally {
      setDeletingId(null);
    }
  };

  /* 导出下载 */
  const handleExport = async (noteId: number, format: "md" | "txt") => {
    if (exportingId !== null) return;
    setExportingId(noteId);
    try {
      await downloadNoteExport(noteId, format);
    } catch (err: any) {
      alert(`导出失败: ${err.message || "未知错误"}`);
    } finally {
      setExportingId(null);
    }
  };

  /* ============ 详情视图 ============ */
  if (detail || detailLoading) {
    return (
      <div className="max-w-3xl mx-auto">
        <DevBanner />
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <button
            onClick={() => handleCloseDetail(false)}
            className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition mb-4"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            返回笔记列表
          </button>

          {detailLoading || !detail ? (
            <div className="text-center py-16">
              <Loader2 className="w-8 h-8 text-gray-700 mx-auto mb-3 animate-spin" />
              <p className="text-sm text-gray-600">加载笔记中...</p>
            </div>
          ) : (
            <div className="bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-6 backdrop-blur-md">
              <h1 className="text-lg font-semibold text-white mb-2">{detail.title}</h1>
              <div className="flex items-center gap-3 flex-wrap text-xs text-gray-600 mb-1">
                {detail.podcast_name && (
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3 h-3" />
                    {detail.podcast_name}
                  </span>
                )}
                {detail.episode_title && <span>{detail.episode_title}</span>}
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(detail.created_at)}
                </span>
                <span>{detail.word_count} 字</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400">{detail.template}</span>
              </div>

              {detail.tags.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap mt-3">
                  <Tag className="w-3 h-3 text-gray-600" />
                  {detail.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-6 pt-4 border-t border-white/[0.06]">
                <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-3">Content</p>
                <div className="prose prose-invert prose-sm max-w-none text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {detail.content}
                </div>
              </div>

              {detail.transcript_text && (
                <details className="mt-6">
                  <summary className="text-xs text-gray-500 hover:text-gray-400 cursor-pointer">
                    查看转录摘要（前 5000 字）
                  </summary>
                  <p className="mt-2 p-3 bg-black/20 rounded-xl text-xs text-gray-500 whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {detail.transcript_text}
                  </p>
                </details>
              )}

              {/* 配图区块：关联图片列表 + 生成入口 */}
              <div className="mt-6 pt-4 border-t border-white/[0.06]">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono flex items-center gap-1.5">
                    <ImageIcon className="w-3 h-3" />
                    Images
                  </p>
                  <button
                    onClick={() => handleGenerateImages(detail.id)}
                    disabled={imageGenerating || imageGenUnavailable}
                    title={imageGenUnavailable ? "图片生成服务不可用（请检查 Playwright/Chromium 是否安装）" : "以本篇笔记标题与内容为素材生成配图"}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {imageGenerating ? (
                      <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    )}
                    <span className="text-xs text-purple-400">
                      {imageGenerating ? "生成中..." : imageGenUnavailable ? "配图服务不可用" : "生成配图"}
                    </span>
                  </button>
                </div>

                {imageError && (
                  <div className="flex items-start gap-2 p-3 mb-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                    <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-400 break-all">{imageError}</p>
                  </div>
                )}

                {imagesLoading ? (
                  <div className="flex items-center justify-center gap-2 py-6">
                    <Loader2 className="w-5 h-5 text-gray-700 animate-spin" />
                    <p className="text-xs text-gray-600">加载配图中...</p>
                  </div>
                ) : noteImages.length > 0 ? (
                  <div className="grid grid-cols-3 gap-3">
                    {noteImages.map((image) => (
                      <div
                        key={image.id}
                        className="group relative rounded-xl overflow-hidden border border-gray-900 hover:border-gray-700 transition cursor-pointer bg-black/20"
                        onClick={() => handleOpenImage(image)}
                        title={`${image.image_name}（点击新窗口查看大图）`}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`/images/${encodeURIComponent(image.image_name)}`}
                          alt={image.image_name}
                          className="w-full aspect-[3/4] object-cover"
                          loading="lazy"
                        />
                        <div className="absolute inset-0 bg-black/60 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition flex items-center justify-center gap-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleOpenImage(image); }}
                            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition"
                            title="新窗口查看大图"
                          >
                            <ExternalLink className="w-4 h-4 text-gray-200" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDownloadImage(image); }}
                            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition"
                            title="下载图片"
                          >
                            <Download className="w-4 h-4 text-emerald-400" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-600 py-2">
                    {imageGenUnavailable
                      ? "配图生成服务当前不可用，可稍后重试或检查服务端环境"
                      : "暂无配图，点击右上角「生成配图」以本篇笔记为素材生成"}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2 mt-6 pt-4 border-t border-white/[0.06]">
                <button
                  onClick={() => handleExport(detail.id, "md")}
                  disabled={exportingId === detail.id}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 transition disabled:opacity-50"
                >
                  {exportingId === detail.id ? (
                    <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin" />
                  ) : (
                    <Download className="w-3.5 h-3.5 text-emerald-400" />
                  )}
                  <span className="text-xs text-emerald-400">导出 Markdown</span>
                </button>
                <button
                  onClick={() => handleExport(detail.id, "txt")}
                  disabled={exportingId === detail.id}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 transition disabled:opacity-50"
                >
                  <FileText className="w-3.5 h-3.5 text-blue-400" />
                  <span className="text-xs text-blue-400">导出纯文本</span>
                </button>
                <button
                  onClick={() => handleDeleteNote(detail)}
                  disabled={deletingId === detail.id}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 transition disabled:opacity-50 ml-auto"
                >
                  {deletingId === detail.id ? (
                    <Loader2 className="w-3.5 h-3.5 text-red-400 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5 text-red-400" />
                  )}
                  <span className="text-xs text-red-400">删除</span>
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    );
  }

  /* ============ 列表视图 ============ */
  return (
    <div className="max-w-3xl mx-auto">
      <DevBanner />

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
          My Notes
        </p>

        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-400/10 flex items-center justify-center">
              <NotebookPen className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-sm font-medium text-white">我的笔记</h1>
              <p className="text-xs text-gray-600">
                共 {total} 篇 · 生成笔记自动保存至此
              </p>
            </div>
          </div>
        </div>

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

        <div className="space-y-2">
          <AnimatePresence mode="wait">
            {loading && notes.length === 0 ? (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-16">
                <Loader2 className="w-8 h-8 text-gray-700 mx-auto mb-3 animate-spin" />
                <p className="text-sm text-gray-600">加载中...</p>
              </motion.div>
            ) : notes.length > 0 ? (
              <motion.div key="note-list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2">
                {notes.map((note, index) => (
                  <motion.div
                    key={note.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.3 }}
                    className="bg-[#0c0c0e]/70 border border-gray-900 rounded-2xl p-4 backdrop-blur-md hover:border-gray-800 transition group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-emerald-400/10 flex items-center justify-center flex-shrink-0">
                        <FileText className="w-5 h-5 text-emerald-400" />
                      </div>

                      <div className="flex-1 min-w-0 cursor-pointer" onClick={() => handleOpenNote(note.id)}>
                        <h3 className="text-sm font-medium text-white truncate">{note.title}</h3>
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                          {note.podcast_name && <span>{note.podcast_name}</span>}
                          <span>{note.word_count} 字</span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(note.created_at)}
                          </span>
                        </div>
                        {note.tags.length > 0 && (
                          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                            {note.tags.slice(0, 4).map((tag) => (
                              <span key={tag} className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px]">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition">
                        <button
                          onClick={() => handleExport(note.id, "md")}
                          disabled={exportingId === note.id}
                          className="p-2 rounded-xl bg-white/5 hover:bg-emerald-500/10 transition disabled:opacity-50"
                          title="导出 Markdown"
                        >
                          {exportingId === note.id ? (
                            <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                          ) : (
                            <Download className="w-4 h-4 text-gray-400 hover:text-emerald-400" />
                          )}
                        </button>
                        <button
                          className="p-2 rounded-xl bg-white/5 hover:bg-red-500/10 transition"
                          title="删除"
                          onClick={() => handleDeleteNote(note)}
                          disabled={deletingId === note.id}
                        >
                          {deletingId === note.id ? (
                            <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                          )}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}

                {hasMore && (
                  <div className="text-center pt-2">
                    <button
                      onClick={() => fetchNotes(notes.length, true)}
                      disabled={loading}
                      className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-xs text-gray-400 transition disabled:opacity-50"
                    >
                      {loading ? "加载中..." : `加载更多（已显示 ${notes.length} / ${total}）`}
                    </button>
                  </div>
                )}
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-16">
                <NotebookPen className="w-12 h-12 text-gray-800 mx-auto mb-4" />
                <p className="text-sm text-gray-600 mb-1">暂无笔记</p>
                <p className="text-xs text-gray-700">
                  前往内容创作生成笔记，生成成功后将自动保存到这里
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
