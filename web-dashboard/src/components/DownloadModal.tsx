"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, X, FileText, Image, FileJson, Archive, Check } from "lucide-react";
import { downloadFile, downloadZip, sanitizeFilename, DownloadFile } from "@/lib/fileDownloader";

interface DownloadOption {
  id: string;
  label: string;
  icon: React.ElementType;
  extension: string;
  mimeType: string;
  content: string;
}

interface DownloadModalProps {
  isOpen: boolean;
  onClose: () => void;
  podcastName: string;
  episodeTitle: string;
  transcriptContent: string;
  noteContent: string;
  jsonContent: string;
  imageUrls?: string[];
}

export default function DownloadModal({
  isOpen,
  onClose,
  podcastName,
  episodeTitle,
  transcriptContent,
  noteContent,
  jsonContent,
  imageUrls = [],
}: DownloadModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set(['transcript_txt', 'note_md']));
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);

  const baseName = sanitizeFilename(`${podcastName}_${episodeTitle}`);

  const options: DownloadOption[] = [
    {
      id: 'transcript_txt',
      label: '转录文本 (TXT)',
      icon: FileText,
      extension: 'txt',
      mimeType: 'text/plain;charset=utf-8',
      content: transcriptContent,
    },
    {
      id: 'note_md',
      label: '笔记 (Markdown)',
      icon: FileText,
      extension: 'md',
      mimeType: 'text/markdown;charset=utf-8',
      content: noteContent,
    },
    {
      id: 'structured_json',
      label: '结构化数据 (JSON)',
      icon: FileJson,
      extension: 'json',
      mimeType: 'application/json;charset=utf-8',
      content: jsonContent,
    },
  ];

  const toggleSelection = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const handleDownload = async () => {
    if (selected.size === 0) return;
    
    setIsDownloading(true);
    setProgress(0);

    const files: DownloadFile[] = options
      .filter(opt => selected.has(opt.id))
      .map(opt => ({
        name: `${baseName}_${opt.id.split('_')[0]}.${opt.extension}`,
        content: opt.content,
        type: opt.mimeType,
      }));

    // Add images if selected
    if (selected.has('images') && imageUrls.length > 0) {
      for (let i = 0; i < imageUrls.length; i++) {
        const url = imageUrls[i];
        try {
          const response = await fetch(url);
          const blob = await response.blob();
          files.push({
            name: `${baseName}_image_${i + 1}.png`,
            content: blob,
            type: 'image/png',
          });
          setProgress(Math.round(((i + 1) / imageUrls.length) * 100));
        } catch (e) {
          console.error('Failed to fetch image:', e);
        }
      }
    }

    if (files.length === 1) {
      downloadFile(files[0]);
    } else {
      await downloadZip(files, `${baseName}_all.zip`);
    }

    setIsDownloading(false);
    setProgress(100);
    setTimeout(() => onClose(), 500);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-surface rounded-2xl border border-border shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Download className="w-5 h-5 text-accent" />
                下载选项
              </h2>
              <button onClick={onClose} className="p-1 rounded-lg hover:bg-surface-subtle">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Options */}
            <div className="p-6 space-y-3">
              {options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => toggleSelection(opt.id)}
                  className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    selected.has(opt.id)
                      ? 'border-accent bg-accent/5'
                      : 'border-border hover:border-text-tertiary'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    selected.has(opt.id) ? 'bg-accent border-accent' : 'border-text-tertiary'
                  }`}>
                    {selected.has(opt.id) && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <opt.icon className="w-5 h-5 text-text-secondary" />
                  <span className="flex-1 text-left font-medium">{opt.label}</span>
                </button>
              ))}

              {/* Images option */}
              {imageUrls.length > 0 && (
                <button
                  onClick={() => toggleSelection('images')}
                  className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    selected.has('images')
                      ? 'border-accent bg-accent/5'
                      : 'border-border hover:border-text-tertiary'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    selected.has('images') ? 'bg-accent border-accent' : 'border-text-tertiary'
                  }`}>
                    {selected.has('images') && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <Image className="w-5 h-5 text-text-secondary" />
                  <span className="flex-1 text-left font-medium">
                    图片 ({imageUrls.length} 张)
                  </span>
                </button>
              )}

              {/* File name */}
              <div className="mt-4">
                <label className="text-xs text-text-tertiary mb-1 block">文件名</label>
                <input
                  type="text"
                  value={baseName}
                  readOnly
                  className="w-full px-3 py-2 bg-surface-subtle border border-border rounded-lg text-sm text-text-tertiary"
                />
              </div>

              {/* Progress */}
              {isDownloading && (
                <div className="mt-4">
                  <div className="h-2 bg-surface-subtle rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-accent rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-text-tertiary mt-1 text-center">{progress}%</p>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleDownload}
                disabled={selected.size === 0 || isDownloading}
                className="px-6 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Archive className="w-4 h-4" />
                {selected.size <= 1 ? '下载' : '打包下载'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
