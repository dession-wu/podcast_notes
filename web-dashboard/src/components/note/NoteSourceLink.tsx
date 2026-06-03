"use client";

import { ExternalLink, MapPin } from "lucide-react";

interface NoteSourceLinkProps {
  onLocate: () => void;
  preview?: string;
  compact?: boolean;
}

export default function NoteSourceLink({ onLocate, preview, compact }: NoteSourceLinkProps) {
  if (compact) {
    return (
      <button
        onClick={onLocate}
        className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded transition hover:opacity-80"
        style={{
          background: "var(--reader-surface)",
          color: "var(--reader-accent)",
          border: "1px solid var(--reader-border)",
        }}
        title="定位到原文"
      >
        <MapPin className="w-3 h-3" />
        原文
      </button>
    );
  }

  return (
    <div
      className="flex items-center gap-2 p-3 rounded-lg border mt-3"
      style={{
        background: "var(--reader-surface)",
        borderColor: "var(--reader-border)",
      }}
    >
      <MapPin className="w-4 h-4 shrink-0" style={{ color: "var(--reader-accent)" }} />
      <div className="flex-1 min-w-0">
        {preview && (
          <p className="text-xs truncate mb-0.5" style={{ color: "var(--reader-text-secondary)" }}>
            {preview}
          </p>
        )}
        <button
          onClick={onLocate}
          className="flex items-center gap-1 text-xs transition hover:opacity-80"
          style={{ color: "var(--reader-accent)" }}
        >
          <ExternalLink className="w-3 h-3" />
          定位到原文位置
        </button>
      </div>
    </div>
  );
}
