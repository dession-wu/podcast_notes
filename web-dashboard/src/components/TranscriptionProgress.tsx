"use client";

import { motion } from "framer-motion";
import { Loader2, Clock, AlertCircle, CheckCircle } from "lucide-react";

interface TranscriptionProgressProps {
  progress: number;
  status: string;
  stage?: string | null;
  estimate?: { formatted_time: string } | null;
  elapsedSeconds?: number | null;
  remainingSeconds?: number | null;
}

export default function TranscriptionProgress({
  progress,
  status,
  stage,
  estimate,
  elapsedSeconds,
  remainingSeconds,
}: TranscriptionProgressProps) {
  const isProcessing = status === "processing" || status === "pending";
  const isCompleted = status === "completed";
  const isFailed = status === "failed";

  // Calculate smooth progress for display
  const displayProgress = Math.min(99, Math.max(5, progress));

  return (
    <div className="w-full" role="region" aria-label="转录进度">
      {/* Status indicator */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isProcessing && (
            <Loader2
              className="w-4 h-4 text-amber-400 animate-spin"
              aria-hidden="true"
            />
          )}
          {isCompleted && (
            <CheckCircle
              className="w-4 h-4 text-emerald-400"
              aria-hidden="true"
            />
          )}
          {isFailed && (
            <AlertCircle
              className="w-4 h-4 text-red-400"
              aria-hidden="true"
            />
          )}
          <span
            className={`text-sm ${
              isProcessing
                ? "text-amber-400"
                : isCompleted
                  ? "text-emerald-400"
                  : isFailed
                    ? "text-red-400"
                    : "text-gray-400"
            }`}
            role="status"
            aria-live="polite"
          >
            {isProcessing
              ? stage || "转录中"
              : isCompleted
                ? "转录完成"
                : isFailed
                  ? "转录失败"
                  : "等待中"}
          </span>
        </div>

        {/* Time estimate */}
        {isProcessing && (remainingSeconds != null || estimate) && (
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Clock className="w-3 h-3" aria-hidden="true" />
            <span>
              {remainingSeconds != null && remainingSeconds > 0
                ? `剩余约 ${Math.ceil(remainingSeconds / 60)} 分钟`
                : estimate?.formatted_time
                  ? `预估 ${estimate.formatted_time}`
                  : "计算中..."}
            </span>
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div
        className="h-2 bg-gray-800 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={displayProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="转录进度百分比"
      >
        <motion.div
          className={`h-full rounded-full ${
            isFailed
              ? "bg-red-500"
              : isCompleted
                ? "bg-emerald-500"
                : "bg-amber-500"
          }`}
          initial={{ width: 0 }}
          animate={{ width: `${displayProgress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Percentage and elapsed time */}
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-600">
          {displayProgress.toFixed(0)}%
        </span>
        {elapsedSeconds != null && (
          <span className="text-xs text-gray-600">
            已用 {Math.floor(elapsedSeconds / 60)} 分钟
          </span>
        )}
      </div>
    </div>
  );
}
