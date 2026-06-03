"use client";

import { Search, X, ChevronUp, ChevronDown } from "lucide-react";
import { useState, useEffect, useRef, useCallback } from "react";

interface ReaderSearchProps {
  isOpen: boolean;
  onClose: () => void;
  content: string;
  onNavigate: (paragraphId: string) => void;
  totalMatches: number;
  currentMatch: number;
  onMatchChange: (index: number) => void;
  onKeywordChange?: (keyword: string) => void;
}

export default function ReaderSearch({
  isOpen,
  onClose,
  content,
  onNavigate,
  totalMatches,
  currentMatch,
  onMatchChange,
  onKeywordChange,
}: ReaderSearchProps) {
  const [keyword, setKeyword] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "Enter") {
        if (e.shiftKey && currentMatch > 0) {
          onMatchChange(currentMatch - 1);
        } else if (!e.shiftKey && currentMatch < totalMatches - 1) {
          onMatchChange(currentMatch + 1);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, currentMatch, totalMatches, onMatchChange, onClose]);

  const prevMatch = useCallback(() => {
    if (currentMatch > 0) {
      onMatchChange(currentMatch - 1);
    }
  }, [currentMatch, onMatchChange]);

  const nextMatch = useCallback(() => {
    if (currentMatch < totalMatches - 1) {
      onMatchChange(currentMatch + 1);
    }
  }, [currentMatch, totalMatches, onMatchChange]);

  if (!isOpen) return null;

  return (
    <div
      className="flex items-center gap-2 px-4 py-2 border-b shrink-0"
      style={{
        background: "var(--reader-surface)",
        borderColor: "var(--reader-border)",
      }}
      role="search"
    >
      <Search className="w-4 h-4 shrink-0" style={{ color: "var(--reader-text-secondary)" }} />

      <input
        ref={inputRef}
        type="text"
        value={keyword}
        onChange={(e) => {
          const newKeyword = e.target.value;
          setKeyword(newKeyword);
          onKeywordChange?.(newKeyword);
        }}
        placeholder="搜索文本..."
        className="flex-1 bg-transparent text-sm outline-none"
        style={{
          color: "var(--reader-text)",
          caretColor: "var(--reader-accent)",
        }}
      />

      {totalMatches > 0 && (
        <span className="text-xs shrink-0" style={{ color: "var(--reader-text-secondary)" }}>
          {currentMatch + 1} / {totalMatches}
        </span>
      )}

      <button
        onClick={prevMatch}
        disabled={totalMatches === 0 || currentMatch === 0}
        className="p-1 rounded transition"
        style={{
          color: currentMatch === 0 || totalMatches === 0 ? "var(--reader-border)" : "var(--reader-text-secondary)",
          opacity: currentMatch === 0 || totalMatches === 0 ? 0.4 : 1,
        }}
        aria-label="上一个匹配"
      >
        <ChevronUp className="w-4 h-4" />
      </button>

      <button
        onClick={nextMatch}
        disabled={totalMatches === 0 || currentMatch >= totalMatches - 1}
        className="p-1 rounded transition"
        style={{
          color: currentMatch >= totalMatches - 1 || totalMatches === 0 ? "var(--reader-border)" : "var(--reader-text-secondary)",
          opacity: currentMatch >= totalMatches - 1 || totalMatches === 0 ? 0.4 : 1,
        }}
        aria-label="下一个匹配"
      >
        <ChevronDown className="w-4 h-4" />
      </button>

      <button
        onClick={onClose}
        className="p-1 rounded transition"
        style={{ color: "var(--reader-text-secondary)" }}
        aria-label="关闭搜索"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
