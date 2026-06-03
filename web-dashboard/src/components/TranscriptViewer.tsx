"use client";

import { useState, useEffect } from "react";
import { getTranscriptContent } from "@/lib/api";
import ReaderShell from "./reader/ReaderShell";
import NoteViewer from "./note/NoteViewer";
import type { NoteData } from "./note/NoteViewer";

interface TranscriptViewerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  text?: string;
  fileId?: string;
  metadata?: {
    word_count?: number;
    language?: string;
    engine_used?: string;
    duration_seconds?: number;
  } | null;
  note?: NoteData | null;
}

export default function TranscriptViewer({
  isOpen,
  onClose,
  title,
  text: initialText,
  fileId,
  metadata,
  note,
}: TranscriptViewerProps) {
  const [text, setText] = useState(initialText || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    if (fileId && !initialText) {
      setLoading(true);
      setError("");
      getTranscriptContent(fileId)
        .then((res) => {
          setText(res.content);
        })
        .catch((err) => {
          setError(err.message || "加载失败");
        })
        .finally(() => {
          setLoading(false);
        });
    } else if (initialText) {
      setText(initialText);
    }
  }, [fileId, initialText, isOpen]);

  const noteContent = note ? (
    <div className="h-full flex flex-col">
      <NoteViewer note={note} />
    </div>
  ) : undefined;

  return (
    <ReaderShell
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      content={text}
      fileId={fileId}
      metadata={metadata}
      loading={loading}
      error={error}
      noteContent={noteContent}
    />
  );
}
