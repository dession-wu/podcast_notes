"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Image,
  Download,
  RotateCcw,
  X,
  CheckCircle,
  Clock,
  Plus,
  Loader2,
  AlertCircle,
  Wand2,
} from "lucide-react";
import {
  startImageGeneration,
  getImageStatus,
  ImageStatusResponse,
} from "@/lib/api";

interface ImageJob {
  id: string;
  title: string;
  status: "generating" | "completed" | "error";
  progress: number;
  result?: ImageStatusResponse["result"];
  error?: string;
  createdAt: string;
}

const styleColors: Record<string, string> = {
  blue: "from-blue-500/20 to-purple-500/20",
  green: "from-emerald-500/20 to-teal-500/20",
  purple: "from-pink-500/20 to-rose-500/20",
};

export default function ImageGenerator() {
  const [jobs, setJobs] = useState<ImageJob[]>([]);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    tags: "",
    podcastName: "",
    episodeTitle: "",
    style: "blue",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<ImageJob | null>(null);

  const pollStatus = async (taskId: string) => {
    try {
      const status = await getImageStatus(taskId);
      setJobs((prev) =>
        prev.map((job) =>
          job.id === taskId
            ? {
                ...job,
                status: status.status as ImageJob["status"],
                progress: status.progress || 0,
                result: status.result || undefined,
                error: status.error || undefined,
              }
            : job
        )
      );
      return status.status === "completed" || status.status === "failed";
    } catch (err) {
      console.error("Polling error:", err);
      return false;
    }
  };

  const handleGenerate = async () => {
    if (!formData.title.trim() || !formData.content.trim()) return;
    setIsSubmitting(true);
    setGlobalError(null);

    try {
      const response = await startImageGeneration({
        title: formData.title,
        content: formData.content,
        tags: formData.tags.split(",").map((t) => t.trim()).filter(Boolean),
        podcast_name: formData.podcastName,
        episode_title: formData.episodeTitle,
        style: formData.style,
        template: "v9",
      });

      const newJob: ImageJob = {
        id: response.task_id,
        title: formData.title,
        status: "generating",
        progress: 10,
        createdAt: new Date().toLocaleDateString("zh-CN"),
      };

      setJobs((prev) => [newJob, ...prev]);
      setFormData({ title: "", content: "", tags: "", podcastName: "", episodeTitle: "", style: "blue" });
      setShowGenerateModal(false);

      const timer = setInterval(async () => {
        const done = await pollStatus(response.task_id);
        if (done) clearInterval(timer);
      }, 3000);
      setTimeout(() => clearInterval(timer), 300000);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  const removeJob = (id: string) => {
    setJobs((prev) => prev.filter((job) => job.id !== id));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono">
          Image Gallery
        </p>
        <button
          onClick={() => setShowGenerateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-white text-black text-xs font-semibold rounded-full hover:bg-gray-100 transition cursor-pointer"
        >
          <Wand2 className="w-3 h-3" />
          生成图片
        </button>
      </div>

      {/* Global Error */}
      <AnimatePresence>
        {globalError && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl"
          >
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <p className="text-xs text-red-400">{globalError}</p>
            <button onClick={() => setGlobalError(null)} className="ml-auto text-gray-500 hover:text-white transition">
              <X className="w-3 h-3" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Generate Modal */}
      <AnimatePresence>
        {showGenerateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            onClick={() => setShowGenerateModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#0c0c0e] border border-gray-900 rounded-3xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-sm font-medium text-white mb-4">生成小红书图片</h3>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">标题</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="笔记标题"
                    className="w-full bg-[#141416] border border-gray-800 rounded-xl py-2.5 px-4 text-sm text-white placeholder:text-gray-700 focus:outline-none focus:border-gray-600"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">内容</label>
                  <textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    placeholder="笔记正文内容..."
                    rows={4}
                    className="w-full bg-[#141416] border border-gray-800 rounded-xl py-2.5 px-4 text-sm text-white placeholder:text-gray-700 focus:outline-none focus:border-gray-600 resize-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1.5 block">播客名称</label>
                    <input
                      type="text"
                      value={formData.podcastName}
                      onChange={(e) => setFormData({ ...formData, podcastName: e.target.value })}
                      placeholder="播客名称"
                      className="w-full bg-[#141416] border border-gray-800 rounded-xl py-2.5 px-4 text-sm text-white placeholder:text-gray-700 focus:outline-none focus:border-gray-600"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1.5 block">单集标题</label>
                    <input
                      type="text"
                      value={formData.episodeTitle}
                      onChange={(e) => setFormData({ ...formData, episodeTitle: e.target.value })}
                      placeholder="单集标题"
                      className="w-full bg-[#141416] border border-gray-800 rounded-xl py-2.5 px-4 text-sm text-white placeholder:text-gray-700 focus:outline-none focus:border-gray-600"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">标签（逗号分隔）</label>
                  <input
                    type="text"
                    value={formData.tags}
                    onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                    placeholder="投资,理财,成长"
                    className="w-full bg-[#141416] border border-gray-800 rounded-xl py-2.5 px-4 text-sm text-white placeholder:text-gray-700 focus:outline-none focus:border-gray-600"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">配色风格</label>
                  <div className="flex gap-2">
                    {[
                      { value: "blue", label: "蓝紫", color: "bg-blue-500" },
                      { value: "green", label: "青绿", color: "bg-emerald-500" },
                      { value: "purple", label: "粉紫", color: "bg-pink-500" },
                    ].map((s) => (
                      <button
                        key={s.value}
                        onClick={() => setFormData({ ...formData, style: s.value })}
                        className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs transition ${
                          formData.style === s.value
                            ? "bg-white/10 border border-white/20 text-white"
                            : "bg-white/5 border border-transparent text-gray-500 hover:bg-white/10"
                        }`}
                      >
                        <div className={`w-3 h-3 rounded-full ${s.color}`} />
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowGenerateModal(false)}
                    className="flex-1 py-2.5 bg-white/5 text-gray-300 text-xs font-medium rounded-xl hover:bg-white/10 transition cursor-pointer border border-white/5"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleGenerate}
                    disabled={isSubmitting || !formData.title.trim() || !formData.content.trim()}
                    className="flex-1 py-2.5 bg-white text-black text-xs font-semibold rounded-xl hover:bg-gray-100 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? (
                      <><Loader2 className="w-3 h-3 animate-spin" />生成中...</>
                    ) : (
                      "开始生成"
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Image Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <AnimatePresence>
          {jobs.map((job, index) => (
            <motion.div
              key={job.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ delay: index * 0.05, duration: 0.4 }}
              className="bg-[#0c0c0e]/70 border border-gray-900 rounded-3xl overflow-hidden backdrop-blur-md hover:border-gray-800 transition group cursor-pointer"
            >
              <div
                className={`aspect-[3/4] bg-gradient-to-br ${
                  styleColors[job.result?.images?.[0] ? "blue" : job.status === "error" ? "purple" : "blue"]
                } flex items-center justify-center relative`}
                onClick={() => job.status === "completed" && setSelectedImage(job)}
              >
                {job.status === "generating" ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                    <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  </div>
                ) : job.status === "error" ? (
                  <AlertCircle className="w-8 h-8 text-red-400/50" />
                ) : (
                  <Image className="w-8 h-8 text-white/20" />
                )}
                {job.status === "completed" && (
                  <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                )}
              </div>
              <div className="p-4">
                <h3 className="text-xs font-medium text-white truncate">{job.title}</h3>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-gray-700 font-mono">
                    {job.status === "generating" ? (
                      <span className="flex items-center gap-1 text-amber-400">
                        <Clock className="w-3 h-3" />生成中
                      </span>
                    ) : job.status === "error" ? (
                      <span className="text-red-400">失败</span>
                    ) : (
                      `${job.result?.count || 0} 张图片`
                    )}
                  </span>
                  <div className="flex items-center gap-1">
                    {job.status === "completed" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedImage(job); }}
                        className="opacity-0 group-hover:opacity-100 transition p-1.5 rounded-lg bg-white/5 hover:bg-white/10"
                      >
                        <Download className="w-3 h-3 text-gray-400" />
                      </button>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); removeJob(job.id); }}
                      className="opacity-0 group-hover:opacity-100 transition p-1.5 rounded-lg bg-white/5 hover:bg-white/10"
                    >
                      <X className="w-3 h-3 text-gray-400" />
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: jobs.length * 0.05, duration: 0.4 }}
          onClick={() => setShowGenerateModal(true)}
          className="aspect-[3/4] bg-[#0c0c0e]/70 border border-gray-900 border-dashed rounded-3xl flex flex-col items-center justify-center gap-3 hover:border-gray-700 transition cursor-pointer backdrop-blur-md"
        >
          <RotateCcw className="w-6 h-6 text-gray-600" />
          <span className="text-xs text-gray-600">生成新图片</span>
        </motion.div>
      </div>

      {jobs.length === 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16">
          <Image className="w-12 h-12 text-gray-800 mx-auto mb-4" />
          <p className="text-sm text-gray-600 mb-1">暂无生成的图片</p>
          <p className="text-xs text-gray-700">点击右上角生成小红书图片</p>
        </motion.div>
      )}

      {/* Preview Modal */}
      <AnimatePresence>
        {selectedImage && selectedImage.result && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            onClick={() => setSelectedImage(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="relative max-w-lg w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setSelectedImage(null)}
                className="absolute -top-10 right-0 p-2 text-gray-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="space-y-3">
                {selectedImage.result.images.map((img, i) => (
                  <div
                    key={img.id}
                    className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-3xl flex items-center justify-center aspect-[3/4]"
                  >
                    <div className="text-center">
                      <Image className="w-16 h-16 text-white/20 mx-auto mb-2" />
                      <p className="text-xs text-gray-500">{img.name}</p>
                      <p className="text-[10px] text-gray-600 mt-1">图片 {i + 1}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex items-center justify-between">
                <h3 className="text-sm text-white">{selectedImage.title}</h3>
                <button className="px-4 py-2 bg-white text-black text-xs font-semibold rounded-full flex items-center gap-2 hover:bg-gray-100 transition cursor-pointer">
                  <Download className="w-3 h-3" />
                  下载全部
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
