"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  FileText,
  RotateCcw,
  Copy,
  Check,
  AlertCircle,
  Mic,
  X,
  Wand2,
} from "lucide-react";
import {
  processContent,
  analyzeContent,
  ProcessResponse,
  TemplateRecommendation,
} from "@/lib/api";
import { getTemplateName } from "@/lib/templates";
import SmartRecommendation from "@/components/template/SmartRecommendation";

export default function ContentProcessor() {
  const [transcript, setTranscript] = useState("");
  const [note, setNote] = useState<ProcessResponse["note"] | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [importedFromTranscription, setImportedFromTranscription] =
    useState(false);

  // Template selection state
  const [recommendation, setRecommendation] =
    useState<TemplateRecommendation | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState("v9");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [usedTemplate, setUsedTemplate] = useState("");
  const [recommendationInfo, setRecommendationInfo] = useState<{
    was_recommended: boolean;
    reason: string;
  } | null>(null);

  // Check for transcript from URL query parameter
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const transcriptText = params.get("transcript");
    if (transcriptText) {
      const decoded = decodeURIComponent(transcriptText);
      setTranscript(decoded);
      setImportedFromTranscription(true);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  // Auto-analyze when transcript changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (transcript.trim().length > 200) {
        handleAnalyze();
      } else {
        setRecommendation(null);
      }
    }, 800);

    return () => clearTimeout(timer);
  }, [transcript]);

  const handleAnalyze = useCallback(async () => {
    if (!transcript.trim() || transcript.length < 200) return;

    setIsAnalyzing(true);
    try {
      const data = await analyzeContent({
        transcript_text: transcript,
      });
      setRecommendation(data.recommendation);
      // Auto-select the recommended template
      setSelectedTemplate(data.recommendation.recommended_template);
    } catch (err) {
      console.error("Analysis error:", err);
      // Silently fail - user can still manually select
    } finally {
      setIsAnalyzing(false);
    }
  }, [transcript]);

  const handleProcess = async () => {
    if (!transcript.trim()) return;
    setIsProcessing(true);
    setError("");
    setUsedTemplate("");
    setRecommendationInfo(null);

    try {
      const data = await processContent({
        transcript_text: transcript,
        template: selectedTemplate,
      });
      setNote(data.note);
      setUsedTemplate(data.used_template);
      if (data.recommendation_info?.was_recommended) {
        setRecommendationInfo({
          was_recommended: true,
          reason: data.recommendation_info.reason,
        });
      }
    } catch (err) {
      setError("处理失败，请检查后端服务是否运行");
      console.error("Process error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCopy = async () => {
    if (!note) return;
    try {
      const text = `${note.title}\n\n${note.content}\n\n${note.tags.map((t) => `#${t}`).join(" ")}`;
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Copy failed:", err);
      alert("复制失败，请手动复制内容");
    }
  };

  const dismissImportNotice = () => {
    setImportedFromTranscription(false);
  };

  const handleAcceptRecommendation = () => {
    if (recommendation) {
      setSelectedTemplate(recommendation.recommended_template);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Input */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Import notice */}
        <AnimatePresence>
          {importedFromTranscription && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-4 flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3"
            >
              <div className="flex items-center gap-2">
                <Mic className="h-4 w-4 text-emerald-400" />
                <p className="text-xs text-emerald-400">
                  已从转录结果导入文本
                </p>
              </div>
              <button
                onClick={dismissImportNotice}
                className="rounded-lg p-1 transition hover:bg-emerald-500/10"
              >
                <X className="h-3 w-3 text-emerald-400" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-4 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4"
            >
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-400" />
              <p className="text-sm text-red-400">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
          <div className="mb-4 flex items-center gap-2">
            <FileText className="h-4 w-4 text-gray-500" />
            <span className="font-mono text-xs uppercase tracking-widest text-gray-500">
              Transcript Input
            </span>
          </div>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="在此粘贴播客转录文本，或从文件库选择音频进行转录..."
            className="h-64 w-full resize-none bg-transparent text-sm leading-relaxed text-gray-300 placeholder-gray-600 focus:outline-none"
          />
          <div className="mt-4 flex items-center justify-between border-t border-white/[0.04] pt-4">
            <span className="text-xs text-gray-600">
              {transcript.length} 字符
              {isAnalyzing && (
                <span className="ml-2 text-amber-400/60">
                  <Wand2 className="mr-1 inline h-3 w-3" />
                  分析中...
                </span>
              )}
            </span>
            <div className="flex gap-2">
              {transcript && (
                <button
                  onClick={() => setTranscript("")}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 transition-colors hover:text-white"
                >
                  <RotateCcw className="h-3 w-3" />
                  清空
                </button>
              )}
              <button
                onClick={handleProcess}
                disabled={isProcessing || !transcript.trim()}
                className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-xs font-medium text-black transition-all hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isProcessing ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                    className="h-3 w-3 rounded-full border-2 border-black/20 border-t-black"
                  />
                ) : (
                  <Sparkles className="h-3 w-3" />
                )}
                {isProcessing ? "处理中..." : "生成笔记"}
              </button>
            </div>
          </div>
        </div>

        {/* Template Selection */}
        <div className="mt-5">
          <SmartRecommendation
            recommendation={recommendation}
            selectedTemplate={selectedTemplate}
            onSelectTemplate={setSelectedTemplate}
            onAcceptRecommendation={handleAcceptRecommendation}
            disabled={isProcessing}
          />
        </div>
      </motion.div>

      {/* Output */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <p className="mb-4 font-mono text-[10px] uppercase tracking-widest text-gray-600">
          Generated Note
        </p>

        <AnimatePresence mode="wait">
          {note ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5"
            >
              {/* Template Info */}
              {usedTemplate && (
                <div className="mb-4 flex items-center justify-between rounded-xl bg-white/5 p-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-3.5 w-3.5 text-amber-400/60" />
                    <span className="text-xs text-white/60">
                      使用模板：
                      <span className="font-medium text-white/80">
                        {getTemplateName(usedTemplate)}
                      </span>
                    </span>
                  </div>
                  {recommendationInfo?.was_recommended && (
                    <span className="text-[10px] text-amber-400/60">
                      {recommendationInfo.reason}
                    </span>
                  )}
                </div>
              )}

              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-medium text-white">
                  {note.title}
                </h3>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 transition-colors hover:text-white"
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-green-400" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                  {copied ? "已复制" : "复制"}
                </button>
              </div>

              <div className="prose prose-invert prose-sm mb-4 max-w-none">
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
                  {note.content}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {note.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="rounded-lg border border-white/[0.06] bg-white/[0.04] px-2 py-1 text-[10px] text-gray-400"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex h-80 items-center justify-center rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5"
            >
              <div className="text-center">
                <Sparkles className="mx-auto mb-3 h-8 w-8 text-gray-700" />
                <p className="text-sm text-gray-600">输入转录文本并点击生成</p>
                <p className="mt-1 text-xs text-gray-700">
                  或前往文件库选择音频自动转录
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
