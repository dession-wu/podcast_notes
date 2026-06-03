"use client";

import { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { FileText, AlertCircle } from "lucide-react";
import PreviewToolbar from "./PreviewToolbar";
import { parseMarkdown } from "@/lib/markdownParser";

interface DocumentPreviewProps {
  content: string;
  fileName?: string;
  fileSize?: number;
}

export default function DocumentPreview({ content, fileName, fileSize }: DocumentPreviewProps) {
  const [zoom, setZoom] = useState(100);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const parsed = useMemo(() => parseMarkdown(content), [content]);

  // Highlight search matches
  const highlightedHtml = useMemo(() => {
    if (!searchQuery) return parsed.html;
    const escaped = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return parsed.html.replace(regex, '<mark class="bg-accent/30 px-0.5 rounded">$1</mark>');
  }, [parsed.html, searchQuery]);

  // Simple pagination: split by headers
  const pages = useMemo(() => {
    const sections = content.split(/(?=^#{1,3}\s)/m).filter(Boolean);
    return sections.length > 0 ? sections : [content];
  }, [content]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
  }, []);

  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-text-tertiary">
        <FileText className="w-12 h-12 mb-4 opacity-50" />
        <p>暂无内容可预览</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface rounded-2xl border border-border overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent" />
          <span className="font-medium text-sm">{parsed.title}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-tertiary">
          <span>{parsed.wordCount} 字</span>
          <span>{parsed.lineCount} 行</span>
          {fileSize && <span>{formatFileSize(fileSize)}</span>}
        </div>
      </div>

      {/* Toolbar */}
      <PreviewToolbar
        zoom={zoom}
        onZoomChange={setZoom}
        onSearch={handleSearch}
        currentPage={currentPage}
        totalPages={pages.length}
        onPageChange={setCurrentPage}
      />

      {/* Content */}
      <motion.div
        className="flex-1 overflow-auto p-6"
        style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
      >
        <div 
          className="prose prose-sm max-w-none prose-headings:text-text-primary prose-p:text-text-secondary prose-strong:text-text-primary prose-blockquote:border-l-accent prose-blockquote:bg-accent/5 prose-code:bg-surface-subtle"
          dangerouslySetInnerHTML={{ __html: highlightedHtml }}
        />
      </motion.div>

      {/* Status Bar */}
      <div className="px-4 py-2 border-t border-border text-xs text-text-tertiary flex items-center justify-between">
        <span>UTF-8</span>
        {searchQuery && (
          <span className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            搜索: "{searchQuery}"
          </span>
        )}
      </div>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
