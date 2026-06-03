"use client";

import {
  Sun,
  Moon,
  Coffee,
  Type,
  AlignJustify,
  Search,
  PanelLeftOpen,
  PanelLeftClose,
  Minus,
  Plus,
  ChevronDown,
  Bookmark,
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useReader } from "./ReaderContext";

interface ReaderToolbarProps {
  currentChapter?: string;
  onSearchOpen: () => void;
  onBookmarkToggle?: () => void;
  isBookmarked?: boolean;
}

const fontOptions: { value: string; label: string }[] = [
  { value: "system", label: "系统默认" },
  { value: "serif", label: "思源宋体" },
  { value: "sans", label: "无衬线" },
  { value: "mono", label: "等宽" },
  { value: "book", label: "阅读体" },
];

const fontSizeLabels: Record<string, string> = {
  xs: "小",
  sm: "较小",
  base: "标准",
  lg: "较大",
  xl: "大",
};

const lineHeightLabels: Record<string, string> = {
  tight: "紧凑",
  normal: "标准",
  relaxed: "宽松",
  loose: "疏朗",
};

export default function ReaderToolbar({
  currentChapter,
  onSearchOpen,
  onBookmarkToggle,
  isBookmarked,
}: ReaderToolbarProps) {
  const { settings, setTheme, setFont, setFontSize, setLineHeight, setScrollSpeed, toggleToc } = useReader();
  const [showFontMenu, setShowFontMenu] = useState(false);
  const [showSizeMenu, setShowSizeMenu] = useState(false);
  const [showLhMenu, setShowLhMenu] = useState(false);
  const fontMenuRef = useRef<HTMLDivElement>(null);
  const sizeMenuRef = useRef<HTMLDivElement>(null);
  const lhMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (fontMenuRef.current && !fontMenuRef.current.contains(e.target as Node)) setShowFontMenu(false);
      if (sizeMenuRef.current && !sizeMenuRef.current.contains(e.target as Node)) setShowSizeMenu(false);
      if (lhMenuRef.current && !lhMenuRef.current.contains(e.target as Node)) setShowLhMenu(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const fontSizeOrder: Array<"xs" | "sm" | "base" | "lg" | "xl"> = ["xs", "sm", "base", "lg", "xl"];
  const currentSizeIdx = fontSizeOrder.indexOf(settings.fontSize);
  const decreaseSize = () => {
    if (currentSizeIdx > 0) setFontSize(fontSizeOrder[currentSizeIdx - 1]);
  };
  const increaseSize = () => {
    if (currentSizeIdx < fontSizeOrder.length - 1) setFontSize(fontSizeOrder[currentSizeIdx + 1]);
  };

  const lhOrder: Array<"tight" | "normal" | "relaxed" | "loose"> = ["tight", "normal", "relaxed", "loose"];
  const currentLhIdx = lhOrder.indexOf(settings.lineHeight);
  const decreaseLh = () => {
    if (currentLhIdx > 0) setLineHeight(lhOrder[currentLhIdx - 1]);
  };
  const increaseLh = () => {
    if (currentLhIdx < lhOrder.length - 1) setLineHeight(lhOrder[currentLhIdx + 1]);
  };

  const themeIcons = {
    light: <Sun className="w-4 h-4" />,
    dark: <Moon className="w-4 h-4" />,
    sepia: <Coffee className="w-4 h-4" />,
  };

  const themeOrder: Array<"dark" | "light" | "sepia"> = ["dark", "light", "sepia"];
  const currentThemeIdx = themeOrder.indexOf(settings.theme);
  const cycleTheme = () => {
    const next = themeOrder[(currentThemeIdx + 1) % themeOrder.length];
    setTheme(next);
  };

  return (
    <div
      className="flex items-center justify-between px-4 py-2.5 border-b shrink-0"
      style={{
        background: "var(--reader-surface)",
        borderColor: "var(--reader-border)",
        backdropFilter: "blur(20px)",
      }}
    >
      {/* Left */}
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={toggleToc}
          className="p-2 rounded-lg transition hover:opacity-80 shrink-0"
          style={{ color: "var(--reader-text-secondary)" }}
          title={settings.showToc ? "关闭目录" : "打开目录"}
          aria-label={settings.showToc ? "关闭目录" : "打开目录"}
        >
          {settings.showToc ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
        </button>
        <span
          className="text-sm truncate max-w-[200px] md:max-w-[300px] hidden sm:block"
          style={{ color: "var(--reader-text)" }}
        >
          {currentChapter || "阅读中"}
        </span>
      </div>

      {/* Right */}
      <div className="flex items-center gap-1 sm:gap-2">
        {/* Bookmark */}
        {onBookmarkToggle && (
          <button
            onClick={onBookmarkToggle}
            className="p-2 rounded-lg transition hover:opacity-80"
            style={{ color: isBookmarked ? "var(--reader-accent)" : "var(--reader-text-secondary)" }}
            title={isBookmarked ? "移除书签" : "添加书签"}
            aria-label={isBookmarked ? "移除书签" : "添加书签"}
          >
            <Bookmark className="w-4 h-4" fill={isBookmarked ? "currentColor" : "none"} />
          </button>
        )}

        {/* Search */}
        <button
          onClick={onSearchOpen}
          className="p-2 rounded-lg transition hover:opacity-80"
          style={{ color: "var(--reader-text-secondary)" }}
          title="搜索"
          aria-label="搜索"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* Theme */}
        <button
          onClick={cycleTheme}
          className="p-2 rounded-lg transition hover:opacity-80"
          style={{ color: "var(--reader-text-secondary)" }}
          title="切换主题"
          aria-label="切换主题"
        >
          {themeIcons[settings.theme]}
        </button>

        {/* Font */}
        <div className="relative hidden md:block" ref={fontMenuRef}>
          <button
            onClick={() => setShowFontMenu((v) => !v)}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs transition hover:opacity-80"
            style={{ color: "var(--reader-text-secondary)" }}
            title="字体"
          >
            <Type className="w-4 h-4" />
            <ChevronDown className="w-3 h-3" />
          </button>
          {showFontMenu && (
            <div
              className="absolute right-0 top-full mt-1 py-1 rounded-lg border shadow-lg z-50 min-w-[120px]"
              style={{ background: "var(--reader-bg)", borderColor: "var(--reader-border)" }}
            >
              {fontOptions.map((f) => (
                <button
                  key={f.value}
                  onClick={() => {
                    setFont(f.value as any);
                    setShowFontMenu(false);
                  }}
                  className="w-full text-left px-3 py-1.5 text-xs transition hover:opacity-80"
                  style={{
                    color: settings.font === f.value ? "var(--reader-accent)" : "var(--reader-text)",
                    fontWeight: settings.font === f.value ? 600 : 400,
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Font Size */}
        <div className="relative" ref={sizeMenuRef}>
          <div className="flex items-center rounded-lg border" style={{ borderColor: "var(--reader-border)" }}>
            <button
              onClick={decreaseSize}
              className="p-1.5 transition hover:opacity-80"
              style={{ color: "var(--reader-text-secondary)" }}
              title="减小字号"
              aria-label="减小字号"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setShowSizeMenu((v) => !v)}
              className="px-1.5 py-1 text-[11px] min-w-[36px] text-center transition hover:opacity-80 hidden sm:block"
              style={{ color: "var(--reader-text-secondary)" }}
            >
              {fontSizeLabels[settings.fontSize]}
            </button>
            <button
              onClick={increaseSize}
              className="p-1.5 transition hover:opacity-80"
              style={{ color: "var(--reader-text-secondary)" }}
              title="增大字号"
              aria-label="增大字号"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          {showSizeMenu && (
            <div
              className="absolute right-0 top-full mt-1 py-1 rounded-lg border shadow-lg z-50 min-w-[80px]"
              style={{ background: "var(--reader-bg)", borderColor: "var(--reader-border)" }}
            >
              {fontSizeOrder.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setFontSize(s);
                    setShowSizeMenu(false);
                  }}
                  className="w-full text-left px-3 py-1.5 text-xs transition hover:opacity-80"
                  style={{
                    color: settings.fontSize === s ? "var(--reader-accent)" : "var(--reader-text)",
                    fontWeight: settings.fontSize === s ? 600 : 400,
                  }}
                >
                  {fontSizeLabels[s]}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Line Height */}
        <div className="relative" ref={lhMenuRef}>
          <div className="flex items-center rounded-lg border" style={{ borderColor: "var(--reader-border)" }}>
            <button
              onClick={decreaseLh}
              className="p-1.5 transition hover:opacity-80"
              style={{ color: "var(--reader-text-secondary)" }}
              title="减小行距"
              aria-label="减小行距"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setShowLhMenu((v) => !v)}
              className="px-1.5 py-1 text-[11px] min-w-[36px] text-center transition hover:opacity-80"
              style={{ color: "var(--reader-text-secondary)" }}
            >
              <AlignJustify className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={increaseLh}
              className="p-1.5 transition hover:opacity-80"
              style={{ color: "var(--reader-text-secondary)" }}
              title="增大行距"
              aria-label="增大行距"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          {showLhMenu && (
            <div
              className="absolute right-0 top-full mt-1 py-1 rounded-lg border shadow-lg z-50 min-w-[80px]"
              style={{ background: "var(--reader-bg)", borderColor: "var(--reader-border)" }}
            >
              {lhOrder.map((lh) => (
                <button
                  key={lh}
                  onClick={() => {
                    setLineHeight(lh);
                    setShowLhMenu(false);
                  }}
                  className="w-full text-left px-3 py-1.5 text-xs transition hover:opacity-80"
                  style={{
                    color: settings.lineHeight === lh ? "var(--reader-accent)" : "var(--reader-text)",
                    fontWeight: settings.lineHeight === lh ? 600 : 400,
                  }}
                >
                  {lineHeightLabels[lh]}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Scroll Speed */}
        <div className="flex items-center gap-1">
          <span className="text-[10px] mr-1 hidden sm:inline" style={{ color: "var(--reader-text-secondary)" }}>
            滚动
          </span>
          {(["slow", "normal", "fast"] as const).map((speed) => (
            <button
              key={speed}
              onClick={() => setScrollSpeed(speed)}
              className="px-1.5 py-0.5 rounded text-[10px] transition"
              style={{
                background: settings.scrollSpeed === speed ? "var(--reader-accent)" : "transparent",
                color: settings.scrollSpeed === speed ? "#fff" : "var(--reader-text-secondary)",
              }}
              title={speed === "slow" ? "慢速滚动" : speed === "normal" ? "正常滚动" : "快速滚动"}
            >
              {speed === "slow" ? "慢" : speed === "normal" ? "中" : "快"}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
