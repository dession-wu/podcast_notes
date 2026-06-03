"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";

export type ReaderTheme = "dark" | "light" | "sepia";
export type ReaderFont = "system" | "serif" | "sans" | "mono" | "book";
export type ReaderFontSize = "xs" | "sm" | "base" | "lg" | "xl";
export type ReaderLineHeight = "tight" | "normal" | "relaxed" | "loose";
export type ReaderScrollSpeed = "slow" | "normal" | "fast";

export interface ReaderSettings {
  theme: ReaderTheme;
  font: ReaderFont;
  fontSize: ReaderFontSize;
  lineHeight: ReaderLineHeight;
  scrollSpeed: ReaderScrollSpeed;
  showToc: boolean;
  showPageNumbers: boolean;
}

const defaultSettings: ReaderSettings = {
  theme: "dark",
  font: "system",
  fontSize: "base",
  lineHeight: "normal",
  scrollSpeed: "normal",
  showToc: true,
  showPageNumbers: false,
};

const STORAGE_KEY = "reader-settings";

interface ReaderContextValue {
  settings: ReaderSettings;
  setTheme: (theme: ReaderTheme) => void;
  setFont: (font: ReaderFont) => void;
  setFontSize: (size: ReaderFontSize) => void;
  setLineHeight: (lh: ReaderLineHeight) => void;
  setScrollSpeed: (speed: ReaderScrollSpeed) => void;
  toggleToc: () => void;
  togglePageNumbers: () => void;
  resetSettings: () => void;
}

const ReaderContext = createContext<ReaderContextValue | null>(null);

export function useReader() {
  const ctx = useContext(ReaderContext);
  if (!ctx) throw new Error("useReader must be used within ReaderProvider");
  return ctx;
}

function loadSettings(): ReaderSettings {
  if (typeof window === "undefined") return defaultSettings;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return { ...defaultSettings, ...JSON.parse(saved) };
  } catch {
    // ignore
  }
  return defaultSettings;
}

function saveSettings(settings: ReaderSettings) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // ignore
  }
}

export function ReaderProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<ReaderSettings>(loadSettings);

  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  const setTheme = useCallback((theme: ReaderTheme) => {
    setSettings((s) => ({ ...s, theme }));
  }, []);

  const setFont = useCallback((font: ReaderFont) => {
    setSettings((s) => ({ ...s, font }));
  }, []);

  const setFontSize = useCallback((fontSize: ReaderFontSize) => {
    setSettings((s) => ({ ...s, fontSize }));
  }, []);

  const setLineHeight = useCallback((lineHeight: ReaderLineHeight) => {
    setSettings((s) => ({ ...s, lineHeight }));
  }, []);

  const setScrollSpeed = useCallback((scrollSpeed: ReaderScrollSpeed) => {
    setSettings((s) => ({ ...s, scrollSpeed }));
  }, []);

  const toggleToc = useCallback(() => {
    setSettings((s) => ({ ...s, showToc: !s.showToc }));
  }, []);

  const togglePageNumbers = useCallback(() => {
    setSettings((s) => ({ ...s, showPageNumbers: !s.showPageNumbers }));
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(defaultSettings);
  }, []);

  return (
    <ReaderContext.Provider
      value={{
        settings,
        setTheme,
        setFont,
        setFontSize,
        setLineHeight,
        setScrollSpeed,
        toggleToc,
        togglePageNumbers,
        resetSettings,
      }}
    >
      {children}
    </ReaderContext.Provider>
  );
}
