"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, FileText, Copy, Check, Download, Loader2, AlertCircle, BookOpen } from "lucide-react";
import { ReaderProvider } from "./ReaderContext";
import ReaderTheme from "./ReaderTheme";
import ReaderToolbar from "./ReaderToolbar";
import ReaderContent, { type ReaderSection } from "./ReaderContent";
import TranscriptContent from "./TranscriptContent";
import ReaderToc from "./ReaderToc";
import ReaderSearch from "./ReaderSearch";
import { useBookmarks } from "./useBookmarks";
import type { TranscriptSegment } from "./TranscriptContent";

interface ReaderShellProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  content: string;
  fileId?: string;
  metadata?: {
    word_count?: number;
    language?: string;
    engine_used?: string;
    duration_seconds?: number;
  } | null;
  loading?: boolean;
  error?: string;
  noteContent?: React.ReactNode;
}

function ShellInner({
  isOpen,
  onClose,
  title,
  content,
  fileId,
  metadata,
  loading,
  error,
  noteContent,
}: ReaderShellProps) {
  const [currentSection, setCurrentSection] = useState<ReaderSection | null>(null);
  const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegment[]>([]);
  const [currentTranscriptSegment, setCurrentTranscriptSegment] = useState<TranscriptSegment | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [currentMatch, setCurrentMatch] = useState(0);
  const [totalMatches, setTotalMatches] = useState(0);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [transcriptContainer, setTranscriptContainer] = useState<HTMLDivElement | null>(null);

  const { bookmarks, toggleBookmark, isBookmarked } = useBookmarks(fileId || "default");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("复制失败:", err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^\w\u4e00-\u9fa5]/g, "_")}_transcript.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "";
    const mins = Math.floor(seconds / 60);
    const hrs = Math.floor(mins / 60);
    if (hrs > 0) {
      return `${hrs}:${(mins % 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;
    }
    return `${mins}:${(seconds % 60).toString().padStart(2, "0")}`;
  };

  const handleBookmarkToggle = () => {
    // 支持转录文本的书签
    if (currentTranscriptSegment) {
      const preview = currentTranscriptSegment.text.slice(0, 100);
      toggleBookmark(currentTranscriptSegment.id, 0, preview);
      return;
    }
    // 支持普通文本的书签
    if (!currentSection) return;
    const paraIndex = 0;
    const preview = currentSection.paragraphs[0] || currentSection.title;
    toggleBookmark(currentSection.id, paraIndex, preview);
  };

  const bookmarked = useMemo(() => {
    if (currentTranscriptSegment) {
      return isBookmarked(currentTranscriptSegment.id, 0);
    }
    return currentSection ? isBookmarked(currentSection.id, 0) : false;
  }, [currentTranscriptSegment, currentSection, isBookmarked]);

  // Detect if content is a transcript format (contains timestamps like [00:00])
  const isTranscript = useMemo(() => {
    return /^\[\d{1,2}:\d{2}/m.test(content);
  }, [content]);

  useEffect(() => {
    if (!searchKeyword.trim()) {
      setTotalMatches(0);
      setCurrentMatch(0);
      return;
    }
    const regex = new RegExp(searchKeyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    const matches = content.match(regex);
    const count = matches ? matches.length : 0;
    setTotalMatches(count);
    setCurrentMatch(0);
  }, [searchKeyword, content]);

  const handleSearchNavigate = useCallback(
    (index: number) => {
      setCurrentMatch(index);
      // Find the nth occurrence and scroll to it
      // 优先使用转录文本容器的引用
      const container = transcriptContainer || contentRef.current;
      if (!container || !searchKeyword) return;
      const marks = container.querySelectorAll("mark");
      if (marks[index]) {
        marks[index].scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    [searchKeyword]
  );

  const handleSearchNavigateById = useCallback(
    (_paragraphId: string) => {
      // Placeholder for paragraph-based navigation
      // Currently using index-based navigation via handleSearchNavigate
    },
    []
  );

  const handleSearchOpen = () => {
    setSearchOpen(true);
  };

  const handleSearchClose = () => {
    setSearchOpen(false);
    setSearchKeyword("");
  };

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "f") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4"
          style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)" }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full sm:h-[85vh] sm:max-w-5xl sm:rounded-2xl overflow-hidden flex flex-col shadow-2xl"
            style={{
              background: "var(--reader-bg)",
              border: "1px solid var(--reader-border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-4 py-3 border-b shrink-0"
              style={{ borderColor: "var(--reader-border)" }}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: "var(--reader-surface)" }}
                >
                  <FileText className="w-4 h-4" style={{ color: "var(--reader-accent)" }} />
                </div>
                <div className="min-w-0">
                  <h3
                    className="text-sm font-medium truncate"
                    style={{ color: "var(--reader-text)" }}
                  >
                    {title}
                  </h3>
                  {metadata && (
                    <p className="text-[10px] mt-0.5" style={{ color: "var(--reader-text-secondary)" }}>
                      {metadata.word_count && `${metadata.word_count} 字`}
                      {metadata.language && ` · ${metadata.language}`}
                      {metadata.duration_seconds && ` · ${formatDuration(metadata.duration_seconds)}`}
                      {metadata.engine_used && ` · ${metadata.engine_used}`}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition hover:opacity-80"
                  style={{
                    background: "var(--reader-surface)",
                    color: copied ? "var(--reader-accent)" : "var(--reader-text-secondary)",
                  }}
                >
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span className="hidden sm:inline">{copied ? "已复制" : "复制"}</span>
                </button>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition hover:opacity-80"
                  style={{
                    background: "var(--reader-surface)",
                    color: "var(--reader-text-secondary)",
                  }}
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">下载</span>
                </button>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg transition hover:opacity-80"
                  style={{ background: "var(--reader-surface)", color: "var(--reader-text-secondary)" }}
                  title="关闭"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Reader Toolbar */}
            <ReaderToolbar
              currentChapter={currentSection?.title}
              onSearchOpen={handleSearchOpen}
              onBookmarkToggle={fileId ? handleBookmarkToggle : undefined}
              isBookmarked={bookmarked}
            />

            {/* Search Bar */}
            {searchOpen && (
              <ReaderSearch
                isOpen={searchOpen}
                onClose={handleSearchClose}
                content={content}
                onNavigate={handleSearchNavigateById}
                totalMatches={totalMatches}
                currentMatch={currentMatch}
                onMatchChange={handleSearchNavigate}
                onKeywordChange={setSearchKeyword}
              />
            )}

            {/* Main Content Area */}
            <div className="flex flex-1 overflow-hidden min-h-0">
              {/* TOC - 支持转录文本目录 */}
              <ReaderToc
                sections={
                  isTranscript
                    ? transcriptSegments.map((seg, idx) => ({
                        id: seg.id,
                        title: seg.speaker
                          ? `${seg.speaker} · ${seg.text.slice(0, 40)}...`
                          : seg.text.slice(0, 50) + (seg.text.length > 50 ? "..." : ""),
                        level: 1,
                        content: seg.text,
                        paragraphs: [seg.text],
                      }))
                    : []
                }
                currentSectionId={currentTranscriptSegment?.id || currentSection?.id}
                onNavigate={(id) => {
                  if (isTranscript) {
                    const el = transcriptContainer?.querySelector(`[data-segment-id="${id}"]`);
                    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                  } else {
                    const el = contentRef.current?.querySelector(`[data-section-id="${id}"]`);
                    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                  }
                }}
              />

              {/* Content */}
              <div className="flex-1 flex flex-col overflow-hidden min-h-0">
                {loading ? (
                  <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--reader-text-secondary)" }} />
                    <span className="ml-2 text-sm" style={{ color: "var(--reader-text-secondary)" }}>
                      加载文本...
                    </span>
                  </div>
                ) : error ? (
                  <div className="flex-1 flex items-center justify-center p-4">
                    <div
                      className="flex items-center gap-2 p-4 rounded-xl border"
                      style={{
                        background: "var(--reader-surface)",
                        borderColor: "var(--reader-border)",
                      }}
                    >
                      <AlertCircle className="w-4 h-4" style={{ color: "var(--reader-accent)" }} />
                      <span className="text-sm" style={{ color: "var(--reader-text)" }}>
                        {error}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div ref={contentRef} className="flex-1 overflow-hidden min-h-0">
                    {isTranscript ? (
                      <TranscriptContent
                        content={content}
                        searchKeyword={searchKeyword}
                        fileId={fileId}
                        onScrollProgress={(progress) => {
                          // Update current section based on scroll for bookmarks
                        }}
                        onSegmentsChange={setTranscriptSegments}
                        onCurrentSegmentChange={setCurrentTranscriptSegment}
                        onContainerRef={setTranscriptContainer}
                      />
                    ) : (
                      <ReaderContent
                        content={content}
                        searchKeyword={searchKeyword}
                        onSectionChange={setCurrentSection}
                      />
                    )}
                  </div>
                )}

                {/* Footer */}
                <div
                  className="px-4 py-2 border-t flex items-center justify-between text-[10px] shrink-0"
                  style={{ borderColor: "var(--reader-border)", color: "var(--reader-text-secondary)" }}
                >
                  <span>{content.length} 字符</span>
                  <div className="flex items-center gap-3">
                    {bookmarks.length > 0 && (
                      <span className="flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        {bookmarks.length} 书签
                      </span>
                    )}
                    <span>{currentSection?.title || ""}</span>
                  </div>
                </div>
              </div>

              {/* Note Panel */}
              {noteContent && (
                <aside
                  className="w-80 shrink-0 border-l overflow-y-auto hidden xl:block reader-scroll"
                  style={{
                    background: "var(--reader-surface)",
                    borderColor: "var(--reader-border)",
                  }}
                >
                  {noteContent}
                </aside>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function ReaderShell(props: ReaderShellProps) {
  return (
    <ReaderProvider>
      <ReaderTheme>
        <ShellInner {...props} />
      </ReaderTheme>
    </ReaderProvider>
  );
}
