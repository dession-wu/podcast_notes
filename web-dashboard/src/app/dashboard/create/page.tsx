"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Image, FileText } from "lucide-react";
import DevBanner from "@/components/DevBanner";
import ContentProcessor from "./ContentProcessor";
import ImageGenerator from "./ImageGenerator";

const tabs = [
  { key: "note", label: "AI 笔记生成", icon: FileText },
  { key: "image", label: "图片生成", icon: Image },
];

export default function CreatePage() {
  const [activeTab, setActiveTab] = useState("note");

  return (
    <div className="max-w-5xl mx-auto">
      <DevBanner />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
          Content Creation
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium transition ${
                activeTab === tab.key
                  ? "bg-white text-black"
                  : "bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-200"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <AnimatePresence mode="wait">
          {activeTab === "note" ? (
            <motion.div
              key="note"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <ContentProcessor />
            </motion.div>
          ) : (
            <motion.div
              key="image"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <ImageGenerator />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
