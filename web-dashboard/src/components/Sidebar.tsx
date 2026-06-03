"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  FolderOpen,
  Sparkles,
  Settings,
  LayoutDashboard,
  Menu,
  X,
  Radio,
} from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "概览", href: "/dashboard" },
  { icon: Search, label: "播客搜索", href: "/dashboard/search" },
  { icon: FolderOpen, label: "文件库", href: "/dashboard/library" },
  { icon: Sparkles, label: "内容创作", href: "/dashboard/create" },
  { icon: Settings, label: "系统设置", href: "/dashboard/settings" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile Toggle */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-4 left-4 z-50 md:hidden w-10 h-10 flex items-center justify-center bg-[#0c0c0e]/90 border border-gray-900 rounded-xl text-gray-400 hover:text-white transition cursor-pointer"
        aria-label="Toggle menu"
      >
        {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Mobile Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{
          x: mobileOpen ? 0 : "-100%",
        }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
        className="fixed md:relative top-0 left-0 h-screen w-[240px] bg-[#0c0c0e]/95 backdrop-blur-xl border-r border-gray-900 flex flex-col z-40 md:translate-x-0"
      >
        {/* Logo */}
        <div className="p-6 border-b border-gray-900">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
              <Radio className="w-4 h-4 text-gray-300" />
            </div>
            <div>
              <div className="text-white font-bold text-sm tracking-wider font-mono">
                PODCAST
              </div>
              <div className="text-[10px] text-gray-600 uppercase tracking-widest font-mono">
                Notes
              </div>
            </div>
          </Link>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                  isActive
                    ? "bg-white/5 text-white border-l-2 border-white"
                    : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.02]"
                }`}
              >
                <item.icon className={`w-4 h-4 ${isActive ? "text-white" : "text-gray-600"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer Status */}
        <div className="p-4 border-t border-gray-900">
          <p className="text-[9px] text-gray-700 tracking-widest font-mono uppercase">
            ● System Active
          </p>
          <p className="text-[9px] text-gray-800 tracking-widest font-mono mt-1">
            v1.0.0_stable
          </p>
        </div>
      </motion.aside>
    </>
  );
}
