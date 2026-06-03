"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, ArrowRight, User, Lock, Mail, Loader2 } from "lucide-react";
import WaveCanvas from "@/components/WaveCanvas";

interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

export default function LandingPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (mode === "register") {
      if (!formData.username.trim()) {
        newErrors.username = "请输入用户名";
      } else if (formData.username.trim().length < 2) {
        newErrors.username = "用户名至少2位";
      }
    }

    if (!formData.email.trim()) {
      newErrors.email = "请输入邮箱";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "邮箱格式不正确";
    }

    if (!formData.password) {
      newErrors.password = "请输入密码";
    } else if (formData.password.length < 6) {
      newErrors.password = "密码至少6位";
    }

    if (mode === "register") {
      if (!formData.confirmPassword) {
        newErrors.confirmPassword = "请确认密码";
      } else if (formData.password !== formData.confirmPassword) {
        newErrors.confirmPassword = "两次密码不一致";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // 清除对应字段错误
    if (errors[field as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
    setFormError("");
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    setFormError("");

    // 模拟API调用
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // 模拟登录/注册成功
    localStorage.setItem("auth_token", "dev");
    window.location.href = "/dashboard";
  };

  const switchMode = () => {
    setMode((prev) => (prev === "login" ? "register" : "login"));
    setErrors({});
    setFormError("");
    setFormData({
      username: "",
      email: "",
      password: "",
      confirmPassword: "",
    });
  };

  return (
    <div className="relative min-h-screen bg-[#030305] overflow-hidden font-sans">
      {/* Wave Canvas Background */}
      <WaveCanvas />

      {/* Content Layer */}
      <div className="relative z-10 w-full min-h-screen flex flex-col justify-between p-6 md:p-8">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="w-full flex justify-between items-center"
        >
          <div className="flex items-center space-x-2">
            <div className="w-5 h-5 bg-white flex items-center justify-center rounded-[3px]">
              <Mic className="text-[#030305] text-[10px] w-3 h-3" />
            </div>
            <span className="text-white font-semibold text-sm tracking-wider font-mono">
              PODCAST NOTES
            </span>
          </div>
          <div className="flex items-center space-x-4 text-[10px] text-gray-500 font-mono">
            <span>SYS_STATUS: ACTIVE</span>
            <span className="text-white/40">|</span>
            <button className="hover:text-white transition-colors cursor-pointer">
              中文 (ZH)
            </button>
          </div>
        </motion.header>

        {/* Main Content */}
        <main className="w-full max-w-7xl mx-auto my-auto grid grid-cols-1 md:grid-cols-12 items-center gap-8">
          {/* Left Side - Project Intro */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="hidden md:block md:col-span-7 pr-12"
          >
            <div className="space-y-2">
              <p className="text-[10px] uppercase tracking-[0.25em] text-blue-400 font-mono font-semibold">
                AI-Powered Podcast Intelligence
              </p>
              <h2 className="text-3xl text-white font-light tracking-tight leading-tight max-w-md">
                从播客中提取洞察，让内容创作更简单
              </h2>
            </div>
          </motion.div>

          {/* Right Side - Auth Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex justify-center md:justify-end md:col-span-5"
          >
            <div className="w-full max-w-[390px] bg-[#09090d]/80 border border-white/[0.06] rounded-2xl p-8 backdrop-blur-xl shadow-[0_24px_80px_rgba(0,0,0,0.8)]">
              {/* Badge & Title */}
              <div className="mb-6">
                <div className="inline-block bg-white/[0.04] border border-white/10 px-2 py-0.5 rounded-[4px]">
                  <span className="text-[9px] font-mono uppercase tracking-widest text-gray-400 font-medium">
                    Uplink Gateway
                  </span>
                </div>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={mode}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                  >
                    <h3 className="text-xl font-medium text-white mt-3 tracking-tight">
                      {mode === "login" ? "登录 / Authenticate" : "注册 / Register"}
                    </h3>
                    <p className="text-xs text-gray-400 mt-1">
                      {mode === "login"
                        ? "输入您的账号信息登录系统"
                        : "创建新账户开始使用"}
                    </p>
                  </motion.div>
                </AnimatePresence>
              </div>

              {/* Form Error */}
              <AnimatePresence>
                {formError && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl"
                  >
                    <p className="text-xs text-red-400">{formError}</p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Form */}
              <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={mode}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-4"
                  >
                    {/* Username (register only) */}
                    {mode === "register" && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                      >
                        <label className="block text-[10px] uppercase tracking-widest text-gray-400 mb-1.5 font-mono font-medium">
                          用户名 / Username
                        </label>
                        <div className="relative">
                          <span className="absolute left-4 top-3.5 text-gray-600 text-xs">
                            <User className="w-3.5 h-3.5" />
                          </span>
                          <input
                            type="text"
                            value={formData.username}
                            onChange={(e) => handleChange("username", e.target.value)}
                            placeholder="输入您的用户名"
                            className={`w-full bg-[#111116] border ${
                              errors.username ? "border-red-500/50" : "border-white/[0.05]"
                            } focus:border-white/20 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none transition-all`}
                          />
                        </div>
                        {errors.username && (
                          <p className="text-[10px] text-red-400 mt-1">{errors.username}</p>
                        )}
                      </motion.div>
                    )}

                    {/* Email */}
                    <div>
                      <label className="block text-[10px] uppercase tracking-widest text-gray-400 mb-1.5 font-mono font-medium">
                        邮箱 / Email
                      </label>
                      <div className="relative">
                        <span className="absolute left-4 top-3.5 text-gray-600 text-xs">
                          <Mail className="w-3.5 h-3.5" />
                        </span>
                        <input
                          type="email"
                          value={formData.email}
                          onChange={(e) => handleChange("email", e.target.value)}
                          placeholder="user@domain.net"
                          className={`w-full bg-[#111116] border ${
                            errors.email ? "border-red-500/50" : "border-white/[0.05]"
                          } focus:border-white/20 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none transition-all`}
                        />
                      </div>
                      {errors.email && (
                        <p className="text-[10px] text-red-400 mt-1">{errors.email}</p>
                      )}
                    </div>

                    {/* Password */}
                    <div>
                      <div className="flex justify-between items-center mb-1.5">
                        <label className="block text-[10px] uppercase tracking-widest text-gray-400 font-mono font-medium">
                          密码 / Password
                        </label>
                        {mode === "login" && (
                          <a
                            href="#"
                            className="text-[10px] text-gray-500 hover:text-white transition-colors"
                          >
                            忘记密码？
                          </a>
                        )}
                      </div>
                      <div className="relative">
                        <span className="absolute left-4 top-3.5 text-gray-600 text-xs">
                          <Lock className="w-3.5 h-3.5" />
                        </span>
                        <input
                          type="password"
                          value={formData.password}
                          onChange={(e) => handleChange("password", e.target.value)}
                          placeholder="••••••••••••"
                          className={`w-full bg-[#111116] border ${
                            errors.password ? "border-red-500/50" : "border-white/[0.05]"
                          } focus:border-white/20 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none transition-all`}
                        />
                      </div>
                      {errors.password && (
                        <p className="text-[10px] text-red-400 mt-1">{errors.password}</p>
                      )}
                    </div>

                    {/* Confirm Password (register only) */}
                    {mode === "register" && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                      >
                        <label className="block text-[10px] uppercase tracking-widest text-gray-400 mb-1.5 font-mono font-medium">
                          确认密码 / Confirm
                        </label>
                        <div className="relative">
                          <span className="absolute left-4 top-3.5 text-gray-600 text-xs">
                            <Lock className="w-3.5 h-3.5" />
                          </span>
                          <input
                            type="password"
                            value={formData.confirmPassword}
                            onChange={(e) => handleChange("confirmPassword", e.target.value)}
                            placeholder="••••••••••••"
                            className={`w-full bg-[#111116] border ${
                              errors.confirmPassword ? "border-red-500/50" : "border-white/[0.05]"
                            } focus:border-white/20 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none transition-all`}
                          />
                        </div>
                        {errors.confirmPassword && (
                          <p className="text-[10px] text-red-400 mt-1">
                            {errors.confirmPassword}
                          </p>
                        )}
                      </motion.div>
                    )}
                  </motion.div>
                </AnimatePresence>

                {/* Submit Button */}
                <button
                  type="submit"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="w-full mt-6 bg-white hover:bg-gray-100 text-black font-semibold text-xs uppercase tracking-widest py-3.5 rounded-full flex items-center justify-center space-x-2 transition-all cursor-pointer active:scale-[0.98] shadow-lg shadow-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>处理中...</span>
                    </>
                  ) : (
                    <>
                      <span>
                        {mode === "login"
                          ? "进入控制台 / Initialize Console"
                          : "创建账户 / Create Account"}
                      </span>
                      <ArrowRight className="w-3 h-3" />
                    </>
                  )}
                </button>
              </form>

              {/* Mode Switch */}
              <div className="mt-6 pt-4 border-t border-white/[0.04] text-center">
                <p className="text-xs text-gray-500">
                  {mode === "login" ? (
                    <>
                      还没有账号？
                      <button
                        onClick={switchMode}
                        className="text-white hover:underline underline-offset-4 ml-1 font-medium cursor-pointer"
                      >
                        立即注册 →
                      </button>
                    </>
                  ) : (
                    <>
                      已有账号？
                      <button
                        onClick={switchMode}
                        className="text-white hover:underline underline-offset-4 ml-1 font-medium cursor-pointer"
                      >
                        立即登录 →
                      </button>
                    </>
                  )}
                </p>
              </div>
            </div>
          </motion.div>
        </main>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.5 }}
          className="w-full flex justify-between items-center text-[9px] text-gray-600 font-mono tracking-widest"
        >
          <div>© 2026 PODCAST NOTES. ALL RIGHTS RESERVED.</div>
          <div className="hidden md:block">SECURE_SSL_ENCRYPTED</div>
        </motion.footer>
      </div>
    </div>
  );
}
