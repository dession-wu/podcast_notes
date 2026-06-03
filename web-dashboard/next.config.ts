import type { NextConfig } from "next";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // Fixed port to avoid conflicts with other projects
  // Use PORT=3001 npm start to start on port 3001
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
    ];
  },
};

export default nextConfig;
