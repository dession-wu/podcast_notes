"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle2, WifiOff } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function DevBanner() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/health/`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });
        if (response.ok) {
          setBackendStatus("connected");
        } else {
          setBackendStatus("disconnected");
        }
      } catch {
        setBackendStatus("disconnected");
      }
    };

    checkBackend();
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  if (backendStatus === "connected") {
    return (
      <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-2xl p-3 mb-6 flex items-start gap-3">
        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-xs text-emerald-400 font-medium">服务已连接</p>
          <p className="text-xs text-gray-500 mt-0.5">
            后端服务运行正常，所有功能可用
          </p>
        </div>
      </div>
    );
  }

  if (backendStatus === "disconnected") {
    return (
      <div className="bg-red-500/5 border border-red-500/10 rounded-2xl p-3 mb-6 flex items-start gap-3">
        <WifiOff className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-xs text-red-400 font-medium">服务未连接</p>
          <p className="text-xs text-gray-500 mt-0.5">
            后端服务未运行，请启动后端服务: <code className="bg-white/5 px-1.5 py-0.5 rounded text-gray-400">python -m uvicorn backend.main:app --port 8001</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber-500/5 border border-amber-500/10 rounded-2xl p-3 mb-6 flex items-start gap-3">
      <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-xs text-amber-400 font-medium">检查连接状态...</p>
        <p className="text-xs text-gray-500 mt-0.5">
          正在检查后端服务状态
        </p>
      </div>
    </div>
  );
}
