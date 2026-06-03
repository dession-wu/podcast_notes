"use client";

import { motion } from "framer-motion";
import { Image, FileText, Check } from "lucide-react";
import {
  TEMPLATE_REGISTRY,
  VISUAL_TEMPLATES,
  TEXT_TEMPLATES,
  getTemplateByAlias,
} from "@/lib/templates";

interface TemplateSelectorProps {
  selectedTemplate: string;
  onSelectTemplate: (alias: string) => void;
  disabled?: boolean;
}

function TemplateCard({
  template,
  isSelected,
  onClick,
  disabled,
}: {
  template: (typeof TEMPLATE_REGISTRY)[0];
  isSelected: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <motion.button
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      onClick={onClick}
      disabled={disabled}
      className={`relative w-full rounded-xl border p-4 text-left transition-all ${
        isSelected
          ? "border-amber-500/50 bg-amber-500/10"
          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
      } ${disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
    >
      {/* Selection Indicator */}
      {isSelected && (
        <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-amber-500">
          <Check className="h-3 w-3 text-black" />
        </div>
      )}

      {/* Icon */}
      <div className="mb-3 flex items-center gap-2">
        {template.is_visual ? (
          <Image className="h-4 w-4 text-sky-400" />
        ) : (
          <FileText className="h-4 w-4 text-emerald-400" />
        )}
        <span
          className={`text-xs ${
            template.is_visual ? "text-sky-400/80" : "text-emerald-400/80"
          }`}
        >
          {template.category}
        </span>
      </div>

      {/* Name & Description */}
      <h4 className="mb-1 text-sm font-semibold text-white">{template.name}</h4>
      <p className="mb-3 text-xs leading-relaxed text-white/50">
        {template.description}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1">
        {template.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="rounded-md bg-white/5 px-2 py-0.5 text-[10px] text-white/40"
          >
            {tag}
          </span>
        ))}
      </div>
    </motion.button>
  );
}

export default function TemplateSelector({
  selectedTemplate,
  onSelectTemplate,
  disabled = false,
}: TemplateSelectorProps) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-5">
      <h3 className="mb-4 text-sm font-medium text-white/80">选择笔记风格</h3>

      {/* Visual Templates */}
      <div className="mb-5">
        <div className="mb-3 flex items-center gap-2">
          <Image className="h-4 w-4 text-sky-400" />
          <span className="text-xs font-medium text-sky-400/80">图文笔记</span>
          <span className="text-xs text-white/30">（生成图文卡片）</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {VISUAL_TEMPLATES.map((template) => (
            <TemplateCard
              key={template.alias}
              template={template}
              isSelected={selectedTemplate === template.alias}
              onClick={() => onSelectTemplate(template.alias)}
              disabled={disabled}
            />
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="mb-5 h-px bg-white/10" />

      {/* Text Templates */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-medium text-emerald-400/80">
            文字笔记
          </span>
          <span className="text-xs text-white/30">（纯文本输出）</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {TEXT_TEMPLATES.map((template) => (
            <TemplateCard
              key={template.alias}
              template={template}
              isSelected={selectedTemplate === template.alias}
              onClick={() => onSelectTemplate(template.alias)}
              disabled={disabled}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
