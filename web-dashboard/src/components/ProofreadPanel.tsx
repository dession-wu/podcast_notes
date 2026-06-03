"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Check, X, Loader2, Sparkles } from "lucide-react";

interface ProofreadIssue {
  id: string;
  line: number;
  original: string;
  suggestion: string;
  type: string;
  context: string;
  accepted: boolean | null;
}

interface ProofreadPanelProps {
  issues: ProofreadIssue[];
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onApplyAll: () => void;
  onIgnoreAll: () => void;
  isLoading: boolean;
}

export default function ProofreadPanel({
  issues,
  onAccept,
  onReject,
  onApplyAll,
  onIgnoreAll,
  isLoading,
}: ProofreadPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const pendingCount = issues.filter(i => i.accepted === null).length;
  const acceptedCount = issues.filter(i => i.accepted === true).length;
  const rejectedCount = issues.filter(i => i.accepted === false).length;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-tertiary">
        <Loader2 className="w-8 h-8 animate-spin mb-3" />
        <p className="text-sm">正在校对文档...</p>
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-tertiary">
        <Sparkles className="w-8 h-8 mb-3 text-success" />
        <p className="text-sm">未发现明显错误</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Stats */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-warning" />
          <span className="font-medium text-sm">发现 {issues.length} 个问题</span>
        </div>
        <div className="flex gap-3 text-xs text-text-tertiary">
          <span className="text-warning">待处理: {pendingCount}</span>
          <span className="text-success">已接受: {acceptedCount}</span>
          <span className="text-text-tertiary">已忽略: {rejectedCount}</span>
        </div>
      </div>

      {/* Issue List */}
      <div className="flex-1 overflow-auto">
        <AnimatePresence>
          {issues.map((issue) => (
            <motion.div
              key={issue.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className={`border-b border-border ${
                issue.accepted === true ? 'bg-success/5' :
                issue.accepted === false ? 'bg-surface-subtle/50 opacity-50' : ''
              }`}
            >
              <button
                onClick={() => setExpandedId(expandedId === issue.id ? null : issue.id)}
                className="w-full px-4 py-3 text-left hover:bg-surface-subtle/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                    issue.type === 'grammar' ? 'bg-warning/10 text-warning' :
                    issue.type === 'spelling' ? 'bg-error/10 text-error' :
                    'bg-info/10 text-info'
                  }`}>
                    {issue.type === 'grammar' ? '语法' :
                     issue.type === 'spelling' ? '拼写' : '标点'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      <span className="line-through text-text-tertiary">{issue.original}</span>
                      {' → '}
                      <span className="text-success font-medium">{issue.suggestion}</span>
                    </p>
                    <p className="text-xs text-text-tertiary mt-1 truncate">
                      第 {issue.line} 行 · {issue.context}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                {issue.accepted === null && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); onAccept(issue.id); }}
                      className="flex items-center gap-1 px-3 py-1 bg-success/10 text-success rounded-lg text-xs font-medium hover:bg-success/20 transition-colors"
                    >
                      <Check className="w-3 h-3" />
                      接受
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onReject(issue.id); }}
                      className="flex items-center gap-1 px-3 py-1 bg-surface-subtle text-text-tertiary rounded-lg text-xs font-medium hover:bg-surface-subtle/80 transition-colors"
                    >
                      <X className="w-3 h-3" />
                      忽略
                    </button>
                  </div>
                )}
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Bulk Actions */}
      {pendingCount > 0 && (
        <div className="px-4 py-3 border-t border-border flex gap-2">
          <button
            onClick={onApplyAll}
            className="flex-1 py-2 bg-success/10 text-success rounded-lg text-xs font-medium hover:bg-success/20 transition-colors"
          >
            全部接受 ({pendingCount})
          </button>
          <button
            onClick={onIgnoreAll}
            className="flex-1 py-2 bg-surface-subtle text-text-tertiary rounded-lg text-xs font-medium hover:bg-surface-subtle/80 transition-colors"
          >
            全部忽略
          </button>
        </div>
      )}
    </div>
  );
}
