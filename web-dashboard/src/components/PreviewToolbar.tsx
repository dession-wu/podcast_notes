"use client";

import { ZoomIn, ZoomOut, Search, ChevronLeft, ChevronRight } from "lucide-react";

interface PreviewToolbarProps {
  zoom: number;
  onZoomChange: (zoom: number) => void;
  onSearch: (query: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const ZOOM_LEVELS = [75, 100, 125, 150];

export default function PreviewToolbar({
  zoom,
  onZoomChange,
  onSearch,
  currentPage,
  totalPages,
  onPageChange,
}: PreviewToolbarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-surface border-b border-border">
      {/* Zoom Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => {
            const idx = ZOOM_LEVELS.indexOf(zoom);
            if (idx > 0) onZoomChange(ZOOM_LEVELS[idx - 1]);
          }}
          disabled={zoom === ZOOM_LEVELS[0]}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
        <button
          onClick={() => {
            const idx = ZOOM_LEVELS.indexOf(zoom);
            if (idx < ZOOM_LEVELS.length - 1) onZoomChange(ZOOM_LEVELS[idx + 1]);
          }}
          disabled={zoom === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>

      {/* Search */}
      <div className="relative flex-1 max-w-xs mx-4">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
        <input
          type="text"
          placeholder="搜索..."
          onChange={(e) => onSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-1.5 bg-surface-subtle border border-border rounded-lg text-sm focus:outline-none focus:border-accent"
        />
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm">
          {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="p-1.5 rounded-lg hover:bg-surface-subtle disabled:opacity-30"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
