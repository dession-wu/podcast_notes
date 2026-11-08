import type { Metadata } from "next";
import "./globals.css";

/*
 * 说明: 原实现使用 next/font/google 的 Noto Sans SC。
 * 该方案在构建期需要访问 fonts.googleapis.com，国内服务器无法连通会导致构建失败，
 * 故改为系统字体栈（见 globals.css 中的 --font-sans 回退链），
 * 本地与容器构建均可离线完成。
 */

export const metadata: Metadata = {
  icons: {
    icon: [{ url: "/brand/icon.svg?v=20261103-brand1", type: "image/svg+xml" }, { url: "/favicon.ico?v=20261103-brand1" }],
    apple: "/brand/icon-180.png",
  },
  title: "播客手账 · 转写与内容整理",
  description: "播客转小红书图文的一站式自动化工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-bg-primary text-text-primary font-sans">
        {children}
      </body>
    </html>
  );
}