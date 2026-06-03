"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { Moon, Bell, User, ChevronLeft, ChevronRight } from "lucide-react";

const routeLabels: Record<string, string> = {
  "/dashboard": "概览",
  "/dashboard/search": "播客搜索",
  "/dashboard/downloads": "下载管理",
  "/dashboard/transcripts": "转录文本",
  "/dashboard/content": "内容提炼",
  "/dashboard/images": "图片生成",
  "/dashboard/publish": "发布管理",
  "/dashboard/settings": "系统设置",
  "/dashboard/library": "文件库",
  "/dashboard/create": "内容创作",
};

export default function TopBar() {
  const pathname = usePathname();
  const label = routeLabels[pathname] || "Dashboard";

  const [canGoBack, setCanGoBack] = useState(false);
  const [canGoForward, setCanGoForward] = useState(false);

  // Update navigation state based on history length
  // Note: We cannot reliably detect forward stack in browsers
  // So we only enable forward button when we know user has gone back
  const [hasGoneBack, setHasGoneBack] = useState(false);

  useEffect(() => {
    const updateNavigationState = () => {
      // Can go back if history length > 1 (not the first page)
      setCanGoBack(window.history.length > 1);
      // Forward is only available if user has gone back before
      setCanGoForward(hasGoneBack);
    };

    updateNavigationState();

    // Listen for popstate (back/forward button usage)
    const handlePopState = () => {
      updateNavigationState();
    };

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [pathname, hasGoneBack]);

  const handleBack = useCallback(() => {
    if (canGoBack) {
      setHasGoneBack(true);
      window.history.back();
    }
  }, [canGoBack]);

  const handleForward = useCallback(() => {
    if (canGoForward) {
      window.history.forward();
    }
  }, [canGoForward]);

  return (
    <header className="h-16 border-b border-gray-900 flex items-center justify-between px-6 md:px-8">
      {/* Left: Navigation + Breadcrumb */}
      <div className="flex items-center gap-4">
        {/* Navigation Buttons */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleBack}
            disabled={!canGoBack}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 border border-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/10 transition cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
            title="后退"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleForward}
            disabled={!canGoForward}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 border border-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/10 transition cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
            title="前进"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Breadcrumb */}
        <div>
          <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-0.5">
            Dashboard
          </p>
          <h1 className="text-white font-semibold text-lg">{label}</h1>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button className="w-9 h-9 flex items-center justify-center rounded-xl bg-white/5 border border-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/10 transition cursor-pointer">
          <Bell className="w-4 h-4" />
        </button>
        <button className="w-9 h-9 flex items-center justify-center rounded-xl bg-white/5 border border-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/10 transition cursor-pointer">
          <Moon className="w-4 h-4" />
        </button>
        <button className="w-9 h-9 flex items-center justify-center rounded-xl bg-white/5 border border-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/10 transition cursor-pointer">
          <User className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
