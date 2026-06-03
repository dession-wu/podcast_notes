"use client";

import { useRef, useEffect, useCallback, useMemo } from "react";
import { useReader } from "./ReaderContext";

export interface ReaderSection {
  id: string;
  title: string;
  level: number;
  content: string;
  paragraphs: string[];
}

interface ReaderContentProps {
  content: string;
  sections?: ReaderSection[];
  searchKeyword?: string;
  onSectionChange?: (section: ReaderSection | null) => void;
  onScrollProgress?: (progress: number) => void;
  highlightParagraph?: string | null;
}

function parseSections(text: string): ReaderSection[] {
  const sections: ReaderSection[] = [];
  const lines = text.split("\n");
  let currentSection: ReaderSection | null = null;
  let currentParagraphs: string[] = [];
  let paragraphBuffer = "";

  function flushParagraph() {
    if (paragraphBuffer.trim()) {
      currentParagraphs.push(paragraphBuffer.trim());
    }
    paragraphBuffer = "";
  }

  function saveSection() {
    if (currentSection) {
      flushParagraph();
      currentSection.paragraphs = currentParagraphs;
      sections.push(currentSection);
      currentSection = null;
      currentParagraphs = [];
    }
  }

  const chapterPatterns = [
    /^##\s+(.+)/,
    /^第[一二三四五六七八九十百千万\d]+[章节部分](.+)?/,
    /^[一二三四五六七八九十]+[、.．](.+)/,
  ];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      if (paragraphBuffer) {
        flushParagraph();
      }
      continue;
    }

    let isChapter = false;
    let level = 1;
    for (const pattern of chapterPatterns) {
      const m = trimmed.match(pattern);
      if (m) {
        isChapter = true;
        level = trimmed.startsWith("##") ? 1 : 2;
        break;
      }
    }

    if (isChapter) {
      saveSection();
      const title = trimmed.replace(/^##\s*/, "").trim();
      currentSection = {
        id: `section-${sections.length + 1}`,
        title,
        level,
        content: "",
        paragraphs: [],
      };
      continue;
    }

    if (paragraphBuffer) {
      paragraphBuffer += " " + trimmed;
    } else {
      paragraphBuffer = trimmed;
    }

    if (line.endsWith("。") || line.endsWith("！") || line.endsWith("？") || line.endsWith(".") || line.endsWith("!") || line.endsWith("?")) {
      if (paragraphBuffer.length > 80 || (paragraphBuffer.length > 20 && Math.random() < 0.3)) {
        flushParagraph();
      }
    }
  }

  saveSection();

  if (sections.length === 0 && text.trim()) {
    const paras = text.split(/\n\n+/).filter((p) => p.trim());
    sections.push({
      id: "section-0",
      title: "",
      level: 0,
      content: text,
      paragraphs: paras,
    });
  }

  return sections;
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightText(text: string, keyword: string): string {
  if (!keyword.trim()) return text;
  const escaped = escapeRegex(keyword);
  return text.replace(new RegExp(`(${escaped})`, "gi"), "<mark>$1</mark>");
}

export default function ReaderContent({
  content,
  sections: providedSections,
  searchKeyword = "",
  onSectionChange,
  onScrollProgress,
  highlightParagraph,
}: ReaderContentProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const sectionsRef = useRef<ReaderSection[]>([]);

  const sections = useMemo(() => {
    if (providedSections && providedSections.length > 0) return providedSections;
    return parseSections(content);
  }, [content, providedSections]);

  sectionsRef.current = sections;

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !onSectionChange) return;

    observerRef.current?.disconnect();

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visible.length > 0) {
          const id = visible[0].target.getAttribute("data-section-id");
          const section = sectionsRef.current.find((s) => s.id === id) || null;
          onSectionChange(section);
        }
      },
      {
        root: container,
        rootMargin: "-20% 0px -60% 0px",
        threshold: [0, 0.25, 0.5, 1],
      }
    );

    container.querySelectorAll("[data-section-id]").forEach((el) => {
      observer.observe(el);
    });

    observerRef.current = observer;

    return () => observer.disconnect();
  }, [sections, onSectionChange]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !onScrollProgress) return;

    const handleScroll = () => {
      const scrollTop = container.scrollTop;
      const scrollHeight = container.scrollHeight - container.clientHeight;
      const progress = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
      onScrollProgress(Math.round(progress));
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, [onScrollProgress]);

  useEffect(() => {
    if (!highlightParagraph || !containerRef.current) return;
    const el = containerRef.current.querySelector(`[data-paragraph-id="${highlightParagraph}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("reader-highlight-pulse");
      setTimeout(() => el.classList.remove("reader-highlight-pulse"), 1500);
    }
  }, [highlightParagraph]);

  const scrollToSection = useCallback((sectionId: string) => {
    const el = containerRef.current?.querySelector(`[data-section-id="${sectionId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  const highlightedContent = useMemo(() => {
    return highlightText(content, searchKeyword);
  }, [content, searchKeyword]);

  return (
    <div
      ref={containerRef}
      className="reader-scroll flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 lg:px-12"
      style={{ background: "var(--reader-bg)" }}
    >
      <div className="max-w-[720px] mx-auto py-8">
        {sections.map((section) => (
          <section
            key={section.id}
            data-section-id={section.id}
            className="mb-8"
          >
            {section.title && (
              <div
                className={`font-semibold mb-4 ${
                  section.level === 1 ? "text-xl" : "text-lg"
                }`}
                style={{ color: "var(--reader-text)" }}
              >
                {highlightText(section.title, searchKeyword)}
              </div>
            )}
            {section.paragraphs.map((para, pIdx) => {
              const paraId = `${section.id}-p${pIdx}`;
              return (
                <p
                  key={paraId}
                  data-paragraph-id={paraId}
                  dangerouslySetInnerHTML={{
                    __html: highlightText(para, searchKeyword),
                  }}
                />
              );
            })}
          </section>
        ))}

        {sections.length === 0 && (
          <div
            dangerouslySetInnerHTML={{ __html: highlightedContent.replace(/\n/g, "<br/>") }}
            className="whitespace-pre-wrap"
          />
        )}
      </div>

      <style>{`
        .reader-highlight-pulse {
          animation: highlightPulse 1.5s ease-out;
        }
        @keyframes highlightPulse {
          0% { background: var(--reader-mark); }
          100% { background: transparent; }
        }
      `}</style>
    </div>
  );
}

export { parseSections, highlightText };
