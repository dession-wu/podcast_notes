"use client";

import { Download, FileText } from "lucide-react";
import { useState } from "react";

export interface NoteData {
  title: string;
  content: string;
  tags: string[];
  stages?: Array<{ stage: string; content: string }>;
  reflections?: Array<{ question: string; answer: string }>;
  source_episode?: string;
  source_podcast?: string;
  word_count?: number;
}

interface NoteExportProps {
  note: NoteData;
  filename?: string;
}

export default function NoteExport({ note, filename }: NoteExportProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const safeName = (note.title || "笔记").replace(/[^\w\u4e00-\u9fa5]/g, "_").slice(0, 30);

  const exportMarkdown = () => {
    setLoading("md");
    try {
      let md = `# ${note.title || "笔记"}\n\n`;

      if (note.tags && note.tags.length > 0) {
        md += `> 标签: ${note.tags.map((t) => `#${t}`).join(" ")}\n\n`;
      }

      if (note.source_podcast) {
        md += `> 来源: ${note.source_podcast}`;
        if (note.source_episode) md += ` - ${note.source_episode}`;
        md += "\n\n";
      }

      md += `---\n\n`;

      md += "## 笔记内容\n\n";
      md += note.content + "\n\n";

      if (note.stages && note.stages.length > 0) {
        md += "## 阶段分析\n\n";
        note.stages.forEach((s, i) => {
          md += `### ${i + 1}. ${s.stage}\n\n`;
          md += s.content + "\n\n";
        });
      }

      if (note.reflections && note.reflections.length > 0) {
        md += "## 反思问答\n\n";
        note.reflections.forEach((r) => {
          md += `**Q: ${r.question}**\n\n${r.answer}\n\n`;
        });
      }

      md += "---\n\n";
      md += `> 字数: ${note.word_count || note.content.length}\n`;
      if (note.source_podcast) {
        md += `> 来源: ${note.source_podcast}${note.source_episode ? ` - ${note.source_episode}` : ""}\n`;
      }

      const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeName}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setLoading(null);
    }
  };

  const exportTxt = () => {
    setLoading("txt");
    try {
      let txt = `${note.title || "笔记"}\n`;
      txt += "=".repeat(20) + "\n\n";

      if (note.tags && note.tags.length > 0) {
        txt += `标签: ${note.tags.join(", ")}\n\n`;
      }

      txt += note.content + "\n\n";

      if (note.stages && note.stages.length > 0) {
        txt += "\n=== 阶段分析 ===\n\n";
        note.stages.forEach((s, i) => {
          txt += `${i + 1}. ${s.stage}\n${s.content}\n\n`;
        });
      }

      if (note.reflections && note.reflections.length > 0) {
        txt += "\n=== 反思问答 ===\n\n";
        note.reflections.forEach((r) => {
          txt += `Q: ${r.question}\nA: ${r.answer}\n\n`;
        });
      }

      if (note.source_podcast) {
        txt += `\n来源: ${note.source_podcast}${note.source_episode ? ` - ${note.source_episode}` : ""}\n`;
      }

      const blob = new Blob([txt], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeName}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setLoading(null);
    }
  };

  const printPdf = () => {
    setLoading("pdf");
    const printContent = `
      <html>
      <head>
        <meta charset="utf-8">
        <title>${note.title || "笔记"}</title>
        <style>
          body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.8; color: #1a1a1a; }
          h1 { font-size: 24px; margin-bottom: 10px; }
          .meta { color: #666; font-size: 13px; margin-bottom: 20px; }
          .tags { margin-bottom: 20px; }
          .tag { display: inline-block; background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 6px; }
          .content { font-size: 15px; white-space: pre-wrap; }
          .stage { margin: 20px 0; padding: 16px; background: #f9f9f9; border-radius: 8px; }
          .stage-title { font-weight: bold; margin-bottom: 8px; }
          .q { color: #4f46e5; font-weight: bold; margin-top: 16px; }
          .footer { margin-top: 40px; color: #999; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }
          @media print { body { margin: 0; padding: 20px; } }
        </style>
      </head>
      <body>
        <h1>${note.title || "笔记"}</h1>
        <div class="meta">
          ${note.word_count ? `${note.word_count} 字` : ""}
          ${note.source_podcast ? ` · 来源: ${note.source_podcast}` : ""}
        </div>
        ${note.tags && note.tags.length > 0 ? `<div class="tags">${note.tags.map((t) => `<span class="tag">#${t}</span>`).join("")}</div>` : ""}
        <div class="content">${note.content.replace(/\n/g, "<br>")}</div>
        ${note.stages && note.stages.length > 0 ? note.stages.map((s, i) => `<div class="stage"><div class="stage-title">${i + 1}. ${s.stage}</div><div>${s.content.replace(/\n/g, "<br>")}</div></div>`).join("") : ""}
        ${note.reflections && note.reflections.length > 0 ? note.reflections.map((r) => `<div class="q">Q: ${r.question}</div><div>${r.answer.replace(/\n/g, "<br>")}</div>`).join("") : ""}
        <div class="footer">
          ${note.source_podcast ? `来源: ${note.source_podcast}${note.source_episode ? ` - ${note.source_episode}` : ""}<br>` : ""}
          导出时间: ${new Date().toLocaleString()}
        </div>
      </body>
      </html>
    `;

    const printWindow = window.open("", "_blank");
    if (printWindow) {
      printWindow.document.write(printContent);
      printWindow.document.close();
      setTimeout(() => {
        printWindow.print();
        setLoading(null);
      }, 300);
    } else {
      setLoading(null);
    }
  };

  return (
    <div className="p-4 border-t" style={{ borderColor: "var(--reader-border)" }}>
      <div className="flex items-center gap-2">
        <button
          onClick={exportMarkdown}
          disabled={!!loading}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs transition hover:opacity-80 disabled:opacity-50"
          style={{
            background: "var(--reader-surface)",
            color: "var(--reader-text)",
            border: "1px solid var(--reader-border)",
          }}
        >
          {loading === "md" ? (
            <span className="animate-spin w-3.5 h-3.5 border border-current border-t-transparent rounded-full" />
          ) : (
            <FileText className="w-3.5 h-3.5" />
          )}
          Markdown
        </button>

        <button
          onClick={exportTxt}
          disabled={!!loading}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs transition hover:opacity-80 disabled:opacity-50"
          style={{
            background: "var(--reader-surface)",
            color: "var(--reader-text)",
            border: "1px solid var(--reader-border)",
          }}
        >
          {loading === "txt" ? (
            <span className="animate-spin w-3.5 h-3.5 border border-current border-t-transparent rounded-full" />
          ) : (
            <FileText className="w-3.5 h-3.5" />
          )}
          TXT
        </button>

        <button
          onClick={printPdf}
          disabled={!!loading}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs transition hover:opacity-80 disabled:opacity-50"
          style={{
            background: "var(--reader-accent)",
            color: "#fff",
          }}
        >
          {loading === "pdf" ? (
            <span className="animate-spin w-3.5 h-3.5 border border-white border-t-transparent rounded-full" />
          ) : (
            <Download className="w-3.5 h-3.5" />
          )}
          PDF
        </button>
      </div>
    </div>
  );
}
