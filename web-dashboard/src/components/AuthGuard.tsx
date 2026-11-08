"use client";
import { useEffect, useState } from "react";
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  useEffect(() => {
    let active = true;
    const verify = async () => {
      try {
        const response = await fetch("/auth/session", { credentials: "same-origin", cache: "no-store" });
        if (response.status !== 204) { window.location.replace("/login"); return; }
        if (active) setAuthenticated(true);
      } catch { window.location.replace("/login"); }
    };
    void verify();
    window.addEventListener("focus", verify);
    return () => { active = false; window.removeEventListener("focus", verify); };
  }, []);
  if (!authenticated) return <div role="status" className="min-h-screen bg-[#050507] flex items-center justify-center text-gray-400">正在验证登录状态……</div>;
  return <>{children}</>;
}