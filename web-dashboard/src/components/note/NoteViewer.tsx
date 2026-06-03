"use client";

import { useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { Copy, Check, ExternalLink, FileText, Layers, MessageSquare } from "lucide-react";

export interface NoteStage {
  stage: string;
  content: string;
}

export interface NoteReflection {
  question: string;
  answer: string;
}

export interface NoteData {
  title: string;
  content: string;
  tags: string[];
  stages?: NoteStage[];
  reflections?: NoteReflection[];
  source_episode?: string;
  source_podcast?: string;
  word_count?: number;
}

interface NoteViewerProps {
  note: NoteData;
  onLocateSource?: () => void;
}

const tagColors = [
  "bg-blue-500/15 text-blue-400",
  "bg-emerald-500/15 text-emerald-400",
  "bg-amber-500/15 text-amber-400",
  "bg-rose-500/15 text-rose-400",
  "bg-violet-500/15 text-violet-400",
  "bg-cyan-500/15 text-cyan-400",
];

function formatContent(text: string): string {
  const dirty = marked.parse(text, { async: false }) as string;
  return DOMPurify.sanitize(dirty);
}

export default function NoteViewer({ note, onLocateSource }: NoteViewerProps) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"content" | "stages" | "reflections">("content");

  const hasStages = note.stages && note.stages.length > 0;
  const hasReflections = note.reflections && note.reflections.length > 0;

  const tabs = [
    { key: "content" as const, label: "笔记内容", icon: <FileText className="w-3.5 h-3.5" />, show: true },
    { key: "stages" as const, label: "阶段分析", icon: <Layers className="w-3.5 h-3.5" />, show: !!hasStages },
    { key: "reflections" as const, label: "反思问答", icon: <MessageSquare className="w-3.5 h-3.5" />, show: !!hasReflections },
  ].filter((t) => t.show);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(note.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b" style={{ borderColor: "var(--reader-border)" }}>
        <h2 className="text-base font-semibold mb-2" style={{ color: "var(--reader-text)" }}>
          {note.title || "笔记"}
        </h2>

        {note.tags && note.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {note.tags.map((tag, idx) => (
              <span
                key={idx}
                className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${tagColors[idx % tagColors.length]}`}
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-3 text-[10px]" style={{ color: "var(--reader-text-secondary)" }}>
          {note.word_count && <span>{note.word_count} 字</span>}
          {note.source_podcast && <span>{note.source_podcast}</span>}
          {onLocateSource && (
            <button
              onClick={onLocateSource}
              className="flex items-center gap-1 hover:opacity-80 transition ml-auto"
              style={{ color: "var(--reader-accent)" }}
            >
              <ExternalLink className="w-3 h-3" />
              <span>定位原文</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      {tabs.length > 1 && (
        <div className="flex border-b" style={{ borderColor: "var(--reader-border)" }}>
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className="flex items-center gap-1.5 px-4 py-2.5 text-xs transition-all border-b-2"
              style={{
                color: activeTab === tab.key ? "var(--reader-accent)" : "var(--reader-text-secondary)",
                borderColor: activeTab === tab.key ? "var(--reader-accent)" : "transparent",
                background: activeTab === tab.key ? "var(--reader-surface)" : "transparent",
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto reader-scroll p-4">
        {activeTab === "content" && (
          <div
            className="prose max-w-none"
            dangerouslySetInnerHTML={{ __html: formatContent(note.content) }}
            style={{
              fontSize: "var(--reader-font-size, 15px)",
              lineHeight: "var(--reader-line-height, 1.6)",
            }}
          />
        )}

        {activeTab === "stages" && note.stages && (
          <div className="space-y-4">
            {note.stages.map((stage, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border"
                style={{
                  background: "var(--reader-surface)",
                  borderColor: "var(--reader-border)",
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{
                      background: "var(--reader-accent)",
                      color: "#fff",
                    }}
                  >
                    {idx + 1}
                  </span>
                  <h3 className="font-medium text-sm" style={{ color: "var(--reader-text)" }}>
                    {stage.stage}
                  </h3>
                </div>
                <div
                  className="text-sm leading-relaxed"
                  style={{ color: "var(--reader-text-secondary)" }}
                  dangerouslySetInnerHTML={{ __html: formatContent(stage.content) }}
                />
              </div>
            ))}
          </div>
        )}

        {activeTab === "reflections" && note.reflections && (
          <div className="space-y-4">
            {note.reflections.map((item, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border"
                style={{
                  background: "var(--reader-surface)",
                  borderColor: "var(--reader-border)",
                }}
              >
                <div className="text-xs font-medium mb-2" style={{ color: "var(--reader-accent)" }}>
                  Q: {item.question}
                </div>
                <div
                  className="text-sm leading-relaxed"
                  style={{ color: "var(--reader-text)" }}
                  dangerouslySetInnerHTML={{ __html: formatContent(item.answer) }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-3 border-t flex items-center justify-end" style={{ borderColor: "var(--reader-border)" }}>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition hover:opacity-80"
          style={{
            background: "var(--reader-surface)",
            color: copied ? "var(--reader-accent)" : "var(--reader-text-secondary)",
          }}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "已复制" : "复制笔记"}
        </button>
      </div>
    </div>
  );
}
