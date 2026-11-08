import type { NextConfig } from "next";

/**
 * 前端部署形态:
 * - 本地开发: Next dev server + rewrites 代理到本地后端 (默认 http://localhost:8000)
 * - 容器部署: NEXT_STATIC_EXPORT=1 时静态导出 (output: 'export')，
 *   由 nginx 托管静态文件并将 /api、/images 反代到 backend:8000（同源，规避 CORS）。
 *   注意: rewrites 与 output: 'export' 互斥，静态导出时必须跳过。
 */
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "1";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  ...(isStaticExport ? { output: "export" as const } : {}),
  ...(!isStaticExport
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*/",
              destination: `${API_BASE_URL}/api/:path*/`,
            },
            {
              source: "/api/:path*",
              destination: `${API_BASE_URL}/api/:path*`,
            },
            /* 生成图片的静态服务代理（backend/main.py 挂载的 /images） */
            {
              source: "/images/:path*",
              destination: `${API_BASE_URL}/images/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;