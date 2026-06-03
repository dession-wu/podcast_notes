"use client";

import { ChevronRight, List } from "lucide-react";
import { useReader } from "./ReaderContext";
import type { ReaderSection } from "./ReaderContent";

interface ReaderTocProps {
  sections: ReaderSection[];
  currentSectionId?: string | null;
  onNavigate: (sectionId: string) => void;
}

export default function ReaderToc({ sections, currentSectionId, onNavigate }: ReaderTocProps) {
  const { settings } = useReader();

  const visibleSections = sections.filter((s) => s.title.trim());

  if (!settings.showToc || visibleSections.length === 0) {
    return null;
  }

  return (
    <aside
      className="w-64 lg:w-72 shrink-0 border-r overflow-y-auto hidden lg:block reader-scroll"
      style={{
        background: "var(--reader-surface)",
        borderColor: "var(--reader-border)",
      }}
    >
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <List className="w-4 h-4" style={{ color: "var(--reader-text-secondary)" }} />
          <span
            className="text-xs font-medium uppercase tracking-wide"
            style={{ color: "var(--reader-text-secondary)" }}
          >
            目录
          </span>
        </div>

        <nav role="navigation" aria-label="文章目录">
          <ul className="space-y-0.5">
            {visibleSections.map((section) => {
              const isActive = section.id === currentSectionId;
              return (
                <li key={section.id}>
                  <button
                    onClick={() => onNavigate(section.id)}
                    className="w-full text-left py-1.5 px-2 rounded-lg text-sm transition-all duration-200 group flex items-start gap-1.5"
                    style={{
                      background: isActive ? "var(--reader-accent)" : "transparent",
                      color: isActive ? "#fff" : "var(--reader-text-secondary)",
                      fontWeight: isActive ? 500 : 400,
                      opacity: isActive ? 1 : 0.75,
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        (e.currentTarget as HTMLButtonElement).style.background = "var(--reader-hover)";
                        (e.currentTarget as HTMLButtonElement).style.opacity = "1";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                        (e.currentTarget as HTMLButtonElement).style.opacity = "0.75";
                      }
                    }}
                    aria-current={isActive ? "location" : undefined}
                  >
                    <ChevronRight
                      className="w-3 h-3 mt-0.5 shrink-0 transition-transform"
                      style={{ transform: isActive ? "rotate(90deg)" : "rotate(0deg)" }}
                    />
                    <span className="line-clamp-2 leading-snug">{section.title}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {visibleSections.length === 0 && (
          <p className="text-xs text-center py-8" style={{ color: "var(--reader-text-secondary)" }}>
            暂无目录
          </p>
        )}
      </div>
    </aside>
  );
}
