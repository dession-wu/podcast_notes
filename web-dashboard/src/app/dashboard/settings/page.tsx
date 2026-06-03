"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Key,
  Mic,
  Search,
  Brain,
  Save,
  Check,
  AlertTriangle,
  HardDrive,
  RotateCcw,
  Loader2,
  FolderOpen,
  CheckCircle2,
  X,
} from "lucide-react";
import DevBanner from "@/components/DevBanner";
import {
  getDownloadSettings,
  updateDownloadSettings,
  resetDownloadSettings,
  validateDownloadPath,
} from "@/lib/api";

interface SettingSection {
  id: string;
  title: string;
  icon: React.ElementType;
  description: string;
  fields: {
    key: string;
    label: string;
    type: "text" | "password" | "select";
    value: string;
    placeholder?: string;
    options?: { value: string; label: string }[];
  }[];
}

const settingsData: SettingSection[] = [
  {
    id: "podcast",
    title: "播客搜索",
    icon: Search,
    description: "配置播客搜索 API 凭据",
    fields: [
      {
        key: "podcastindex_key",
        label: "PodcastIndex API Key",
        type: "text",
        value: "",
        placeholder: "输入 API Key",
      },
      {
        key: "podcastindex_secret",
        label: "PodcastIndex API Secret",
        type: "password",
        value: "",
        placeholder: "输入 API Secret",
      },
    ],
  },
  {
    id: "llm",
    title: "LLM 服务",
    icon: Brain,
    description: "配置大语言模型提供商",
    fields: [
      {
        key: "llm_provider",
        label: "提供商",
        type: "select",
        value: "openai",
        options: [
          { value: "openai", label: "OpenAI" },
          { value: "anthropic", label: "Anthropic" },
          { value: "ollama", label: "Ollama (本地)" },
        ],
      },
      {
        key: "llm_api_key",
        label: "API Key",
        type: "password",
        value: "",
        placeholder: "输入 LLM API Key",
      },
    ],
  },
  {
    id: "stt",
    title: "语音转录",
    icon: Mic,
    description: "配置语音识别引擎",
    fields: [
      {
        key: "stt_engine",
        label: "引擎",
        type: "select",
        value: "whisper",
        options: [
          { value: "whisper", label: "OpenAI Whisper" },
          { value: "faster-whisper", label: "Faster Whisper" },
          { value: "sensevoice", label: "SenseVoice" },
        ],
      },
      {
        key: "stt_api_key",
        label: "API Key (可选)",
        type: "password",
        value: "",
        placeholder: "某些引擎需要 API Key",
      },
    ],
  },
];

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [formData, setFormData] = useState<Record<string, string>>({
    podcastindex_key: "",
    podcastindex_secret: "",
    llm_provider: "openai",
    llm_api_key: "",
    stt_engine: "whisper",
    stt_api_key: "",
  });

  // Download path state
  const [downloadPath, setDownloadPath] = useState("");
  const [isCustomPath, setIsCustomPath] = useState(false);
  const [customPath, setCustomPath] = useState("");
  const [pathError, setPathError] = useState("");
  const [pathLoading, setPathLoading] = useState(false);
  const [pathValidation, setPathValidation] = useState<{
    valid: boolean;
    message: string;
    checking: boolean;
  }>({ valid: true, message: "", checking: false });
  const [showPathConfirm, setShowPathConfirm] = useState(false);
  const [pendingPath, setPendingPath] = useState("");
  const [pathSuccess, setPathSuccess] = useState("");

  useEffect(() => {
    getDownloadSettings()
      .then((res) => {
        setDownloadPath(res.current_path);
        setIsCustomPath(res.is_custom);
      })
      .catch(() => {
        // silently fail
      });
  }, []);

  // Real-time path validation with debounce
  useEffect(() => {
    if (!customPath.trim()) {
      setPathValidation({ valid: true, message: "", checking: false });
      return;
    }
    setPathValidation((prev) => ({ ...prev, checking: true }));
    const timer = setTimeout(async () => {
      try {
        const result = await validateDownloadPath(customPath.trim());
        setPathValidation({
          valid: result.valid,
          message: result.valid ? "路径可用" : (result.error || "路径无效"),
          checking: false,
        });
      } catch {
        setPathValidation({ valid: false, message: "验证失败", checking: false });
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [customPath]);

  const handleChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    // TODO: API call to save settings
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleSavePath = async () => {
    if (!pendingPath.trim()) return;
    setPathLoading(true);
    try {
      const validation = await validateDownloadPath(pendingPath.trim());
      if (!validation.valid) {
        setPathError(validation.error || "路径无效");
        setPathLoading(false);
        return;
      }
      const res = await updateDownloadSettings(pendingPath.trim());
      setDownloadPath(res.current_path);
      setIsCustomPath(true);
      setCustomPath("");
      setPathError("");
      setPathSuccess("下载路径已更新");
      setTimeout(() => setPathSuccess(""), 3000);
    } catch (e: any) {
      setPathError(e.message || "保存失败");
    } finally {
      setPathLoading(false);
      setShowPathConfirm(false);
      setPendingPath("");
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <DevBanner />

        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-mono mb-4">
          System Configuration
        </p>

        {/* Warning */}
        <div className="bg-amber-500/5 border border-amber-500/10 rounded-2xl p-4 mb-6 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs text-amber-400 font-medium">安全提示</p>
            <p className="text-xs text-gray-500 mt-1">
              API 密钥仅存储在本地，不会上传到任何服务器。请妥善保管你的凭据。
            </p>
          </div>
        </div>

        {/* Settings Sections */}
        <div className="space-y-6">
          {settingsData.map((section, index) => {
            const SectionIcon = section.icon;
            return (
              <motion.div
                key={section.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                className="bg-[#0c0c0e]/70 border border-gray-900 rounded-3xl p-6 backdrop-blur-md"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                    <SectionIcon className="w-4 h-4 text-gray-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      {section.title}
                    </h3>
                    <p className="text-xs text-gray-600">
                      {section.description}
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  {section.fields.map((field) => (
                    <div key={field.key}>
                      <label className="block text-[10px] uppercase tracking-wider text-gray-500 mb-1.5 font-medium">
                        {field.label}
                      </label>
                      {field.type === "select" ? (
                        <select
                          value={formData[field.key]}
                          onChange={(e) =>
                            handleChange(field.key, e.target.value)
                          }
                          className="w-full bg-[#141416] border border-gray-900 rounded-xl px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-gray-700 transition appearance-none cursor-pointer"
                        >
                          {field.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.type}
                          value={formData[field.key]}
                          onChange={(e) =>
                            handleChange(field.key, e.target.value)
                          }
                          placeholder={field.placeholder}
                          className="w-full bg-[#141416] border border-gray-900 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-700 transition"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Storage Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="bg-[#0c0c0e]/70 border border-gray-900 rounded-3xl p-6 backdrop-blur-md mt-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
              <HardDrive className="w-4 h-4 text-gray-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">存储设置</h3>
              <p className="text-xs text-gray-600">配置音频下载保存位置</p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Current path display */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 mb-1.5 font-medium">
                当前下载目录
              </label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-[#141416] border border-gray-900 rounded-xl px-4 py-3 text-sm text-gray-400 flex items-center gap-2">
                  <FolderOpen className="w-4 h-4 text-gray-600 flex-shrink-0" />
                  <span className="truncate">{downloadPath || "加载中..."}</span>
                </div>
                {isCustomPath && (
                  <button
                    onClick={async () => {
                      setPathLoading(true);
                      try {
                        const res = await resetDownloadSettings();
                        setDownloadPath(res.current_path);
                        setIsCustomPath(false);
                        setPathError("");
                        setPathSuccess("已恢复默认路径");
                        setTimeout(() => setPathSuccess(""), 3000);
                      } catch (e: any) {
                        setPathError(e.message || "重置失败");
                      } finally {
                        setPathLoading(false);
                      }
                    }}
                    disabled={pathLoading}
                    className="px-4 py-3 bg-white/5 border border-gray-800 rounded-xl text-xs text-gray-400 hover:text-white hover:bg-white/10 transition disabled:opacity-50"
                    title="恢复默认路径"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                )}
              </div>
              {isCustomPath && (
                <p className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  已使用自定义路径
                </p>
              )}
            </div>

            {/* New path input */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 mb-1.5 font-medium">
                自定义下载目录
              </label>
              <div className="flex items-center gap-2">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={customPath}
                    onChange={(e) => {
                      setCustomPath(e.target.value);
                      setPathError("");
                    }}
                    placeholder="输入完整路径，如 D:\\Podcasts\\Downloads"
                    className={`w-full bg-[#141416] border rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none transition ${
                      pathValidation.checking
                        ? "border-gray-700"
                        : pathValidation.message
                        ? pathValidation.valid
                          ? "border-emerald-500/30 focus:border-emerald-500/50"
                          : "border-red-500/30 focus:border-red-500/50"
                        : "border-gray-900 focus:border-gray-700"
                    }`}
                  />
                  {pathValidation.checking && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 animate-spin" />
                  )}
                </div>
                <button
                  onClick={() => {
                    if (!customPath.trim()) return;
                    setPendingPath(customPath.trim());
                    setShowPathConfirm(true);
                  }}
                  disabled={pathLoading || !customPath.trim() || !pathValidation.valid || pathValidation.checking}
                  className="px-4 py-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 hover:bg-emerald-500/20 transition disabled:opacity-50"
                >
                  {pathLoading ? "处理中..." : "保存"}
                </button>
              </div>
              {pathValidation.message && !pathValidation.checking && (
                <p className={`text-[10px] mt-1 flex items-center gap-1 ${pathValidation.valid ? "text-emerald-400" : "text-red-400"}`}>
                  {pathValidation.valid ? <CheckCircle2 className="w-3 h-3" /> : <X className="w-3 h-3" />}
                  {pathValidation.message}
                </p>
              )}
              {pathError && (
                <p className="text-[10px] text-red-400 mt-1">{pathError}</p>
              )}
              {pathSuccess && (
                <p className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  {pathSuccess}
                </p>
              )}
            </div>
          </div>
        </motion.div>

        {/* Save Button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 flex items-center justify-end gap-4"
        >
          {saved && (
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <Check className="w-3 h-3" />
              已保存
            </span>
          )}
          <button
            onClick={handleSave}
            className="px-6 py-3 bg-white text-black font-semibold text-xs uppercase tracking-wider rounded-full flex items-center gap-2 hover:bg-gray-100 transition cursor-pointer"
          >
            <Save className="w-4 h-4" />
            保存设置
          </button>
        </motion.div>
      </motion.div>

      {/* Path Change Confirmation Dialog */}
      <AnimatePresence>
        {showPathConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center"
            onClick={() => setShowPathConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[#0c0c0e] border border-gray-800 rounded-2xl p-6 max-w-md w-full mx-4"
            >
              <h4 className="text-sm font-medium text-white mb-2">确认更改下载位置？</h4>
              <p className="text-xs text-gray-500 mb-4">
                新位置: <span className="text-gray-300 font-mono">{pendingPath}</span>
              </p>
              <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 mb-4">
                <p className="text-[11px] text-gray-500">
                  更改后，<span className="text-gray-300">新下载的文件</span>将保存到此位置。
                  已有文件不会自动移动。
                </p>
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowPathConfirm(false);
                    setPendingPath("");
                  }}
                  className="px-4 py-2 text-xs text-gray-400 hover:text-white transition"
                >
                  取消
                </button>
                <button
                  onClick={handleSavePath}
                  disabled={pathLoading}
                  className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 hover:bg-emerald-500/20 transition disabled:opacity-50"
                >
                  {pathLoading ? (
                    <span className="flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      保存中...
                    </span>
                  ) : (
                    "确认更改"
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
