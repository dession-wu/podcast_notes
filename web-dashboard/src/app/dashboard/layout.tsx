"use client";

import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import WaveCanvas from "@/components/WaveCanvas";
import AuthGuard from "@/components/AuthGuard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="relative min-h-screen bg-[#050507] overflow-hidden">
        {/* Wave Canvas Background */}
        <WaveCanvas />

        {/* Content Layer */}
        <div className="relative z-10 flex min-h-screen">
          {/* Sidebar */}
          <Sidebar />

          {/* Main Content */}
          <div className="flex-1 flex flex-col min-h-screen md:ml-0">
            <TopBar />
            <main className="flex-1 p-6 md:p-8 overflow-y-auto">
              {children}
            </main>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
