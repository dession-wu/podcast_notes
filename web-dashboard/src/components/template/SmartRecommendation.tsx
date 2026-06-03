"use client";

import { motion } from "framer-motion";
import { Sparkles, Check, ChevronDown, Wand2 } from "lucide-react";
import { useState } from "react";
import { TemplateRecommendation } from "@/lib/api";
import { getTemplateByAlias } from "@/lib/templates";
import TemplateSelector from "./TemplateSelector";

interface SmartRecommendationProps {
  recommendation: TemplateRecommendation | null;
  selectedTemplate: string;
  onSelectTemplate: (alias: string) => void;
  onAcceptRecommendation: () => void;
  disabled?: boolean;
}

export default function SmartRecommendation({
  recommendation,
  selectedTemplate,
  onSelectTemplate,
  onAcceptRecommendation,
  disabled = false,
}: SmartRecommendationProps) {
  const [showSelector, setShowSelector] = useState(false);

  if (!recommendation) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
        <Wand2 className="mx-auto mb-3 h-6 w-6 text-white/30" />
        <p className="text-sm text-white/50">
          输入转录文本后，系统将智能推荐最适合的笔记风格
        </p>
      </div>
    );
  }

  const recommendedTemplate = getTemplateByAlias(recommendation.recommended_template);
  const isRecommendedSelected = selectedTemplate === recommendation.recommended_template;

  return (
    <div className="space-y-4">
      {/* Smart Recommendation Card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className={`relative rounded-2xl border p-6 transition-all ${
          isRecommendedSelected
            ? "border-amber-500/40 bg-gradient-to-br from-amber-500/10 to-orange-500/5"
            : "border-white/10 bg-white/5"
        }`}
      >
        {/* Badge */}
        <div className="mb-4 flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full bg-amber-500/20 px-3 py-1">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-xs font-medium text-amber-300">
              系统推荐
            </span>
          </div>
          <span className="text-xs text-white/40">
            置信度 {Math.round(recommendation.confidence * 100)}%
          </span>
        </div>

        {/* Template Info */}
        <div className="mb-4">
          <h3 className="mb-1 text-lg font-semibold text-white">
            {recommendation.recommended_name}
          </h3>
          <p className="text-sm text-white/60">
            {recommendedTemplate?.description}
          </p>
        </div>

        {/* Reason */}
        <div className="mb-5 rounded-xl bg-white/5 p-3">
          <p className="text-sm text-white/70">
            <span className="text-amber-400/80">原因：</span>
            {recommendation.reason}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onAcceptRecommendation}
            disabled={disabled || isRecommendedSelected}
            className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition-all ${
              isRecommendedSelected
                ? "cursor-default bg-emerald-500/20 text-emerald-400"
                : "bg-amber-500/20 text-amber-300 hover:bg-amber-500/30"
            }`}
          >
            {isRecommendedSelected ? (
              <>
                <Check className="h-4 w-4" />
                已选择
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                使用推荐
              </>
            )}
          </button>

          <button
            onClick={() => setShowSelector(!showSelector)}
            disabled={disabled}
            className="flex items-center gap-1.5 rounded-xl border border-white/10 px-4 py-2.5 text-sm text-white/60 transition-all hover:bg-white/5 hover:text-white/80"
          >
            选择其他
            <ChevronDown
              className={`h-4 w-4 transition-transform ${
                showSelector ? "rotate-180" : ""
              }`}
            />
          </button>
        </div>
      </motion.div>

      {/* Template Selector Dropdown */}
      {showSelector && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
        >
          <TemplateSelector
            selectedTemplate={selectedTemplate}
            onSelectTemplate={(alias) => {
              onSelectTemplate(alias);
              setShowSelector(false);
            }}
            disabled={disabled}
          />
        </motion.div>
      )}
    </div>
  );
}
