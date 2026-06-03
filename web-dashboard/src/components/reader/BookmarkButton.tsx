"use client";

import { Bookmark, Trash2 } from "lucide-react";
import { useBookmarks, Bookmark as BookmarkType } from "./useBookmarks";

interface BookmarkButtonProps {
  fileId: string;
  sectionId: string;
  paragraphIndex: number;
  preview: string;
  onNavigate?: (bookmark: BookmarkType) => void;
  showRemove?: boolean;
}

export default function BookmarkButton({
  fileId,
  sectionId,
  paragraphIndex,
  preview,
  onNavigate,
  showRemove,
}: BookmarkButtonProps) {
  const { bookmarks, toggleBookmark, isBookmarked } = useBookmarks(fileId);
  const bookmarked = isBookmarked(sectionId, paragraphIndex);

  const handleClick = () => {
    if (bookmarked && showRemove) {
      const existing = bookmarks.find(
        (b) => b.sectionId === sectionId && b.paragraphIndex === paragraphIndex
      );
      if (existing) {
        toggleBookmark(sectionId, paragraphIndex, preview);
      }
    } else {
      toggleBookmark(sectionId, paragraphIndex, preview);
    }
  };

  if (onNavigate) {
    const existing = bookmarks.find(
      (b) => b.sectionId === sectionId && b.paragraphIndex === paragraphIndex
    );
    if (existing) {
      return (
        <button
          onClick={() => onNavigate(existing)}
          className="flex items-center gap-1.5 text-xs p-1.5 rounded transition hover:opacity-80"
          style={{ color: "var(--reader-accent)" }}
          title="跳转到书签"
        >
          <Bookmark className="w-3.5 h-3.5" fill="currentColor" />
          {preview && <span className="truncate max-w-[120px]">{preview}</span>}
        </button>
      );
    }
    return null;
  }

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-1.5 text-xs p-1.5 rounded transition hover:opacity-80"
      style={{
        color: bookmarked ? "var(--reader-accent)" : "var(--reader-text-secondary)",
      }}
      title={bookmarked ? "移除书签" : "添加书签"}
      aria-label={bookmarked ? "移除书签" : "添加书签"}
    >
      <Bookmark
        className="w-4 h-4"
        fill={bookmarked ? "currentColor" : "none"}
      />
      {bookmarked && showRemove && (
        <Trash2 className="w-3 h-3" />
      )}
    </button>
  );
}
