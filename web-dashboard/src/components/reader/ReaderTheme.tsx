"use client";

import { useEffect } from "react";
import { useReader } from "./ReaderContext";

const fontMap: Record<string, string> = {
  system: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  serif: '"Noto Serif SC", "Source Han Serif SC", Georgia, "Times New Roman", serif',
  sans: '"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
  mono: '"JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace',
  book: '"LXGW WenKai", "Ma Shan Zheng", "Noto Serif SC", serif',
};

const sizeMap: Record<string, string> = {
  xs: "14px",
  sm: "15px",
  base: "16px",
  lg: "18px",
  xl: "20px",
};

const lineHeightMap: Record<string, string> = {
  tight: "1.4",
  normal: "1.6",
  relaxed: "1.8",
  loose: "2.0",
};

export default function ReaderTheme({ children }: { children: React.ReactNode }) {
  const { settings } = useReader();

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--reader-font-family", fontMap[settings.font] || fontMap.system);
    root.style.setProperty("--reader-font-size", sizeMap[settings.fontSize] || sizeMap.base);
    root.style.setProperty("--reader-line-height", lineHeightMap[settings.lineHeight] || lineHeightMap.normal);

    // Apply theme class to body for global theme styling
    document.body.classList.remove("reader-theme-dark", "reader-theme-light", "reader-theme-sepia");
    document.body.classList.add(`reader-theme-${settings.theme}`);

    return () => {
      document.body.classList.remove("reader-theme-dark", "reader-theme-light", "reader-theme-sepia");
    };
  }, [settings.font, settings.fontSize, settings.lineHeight, settings.theme]);

  return <>{children}</>;
}
