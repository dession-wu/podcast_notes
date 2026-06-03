"use client";

import { useRef, useEffect, useCallback, useMemo, useState } from "react";
import { useReader } from "./ReaderContext";
import { Clock, User, Play } from "lucide-react";

export interface TranscriptSegment {
  id: string;
  time: string;
  speaker: string | null;
  text: string;
  isEstimated?: boolean;
  confidence?: number;
}

interface TranscriptContentProps {
  content: string;
  searchKeyword?: string;
  onScrollProgress?: (progress: number) => void;
  fileId?: string;
  onSegmentsChange?: (segments: TranscriptSegment[]) => void;
  onCurrentSegmentChange?: (segment: TranscriptSegment | null) => void;
  onContainerRef?: (container: HTMLDivElement | null) => void;
}

// ============================================
// 智能转录解析器
// ============================================

// 支持多种转录格式：
// 1. [00:00] Speaker: text
// 2. [00:00] text (无说话人)
// 3. 00:00 Speaker: text
// 4. Speaker: text (无时间戳)
// 5. 纯文本段落（自动智能分段）

function parseTranscript(text: string): { segments: TranscriptSegment[]; isTranscript: boolean } {
  const lines = text.split("\n");

  // 检测格式类型
  const hasTimestamps = lines.some((l) => /^\[\d{1,2}:\d{2}/.test(l.trim()));
  const hasSpeakers = lines.some((l) => /^[A-Z][a-zA-Z\s]+:/.test(l.trim()));

  // 如果有多行包含时间戳或说话人，使用标准解析
  const timestampLines = lines.filter((l) => /^\[\d{1,2}:\d{2}/.test(l.trim()));
  const speakerLines = lines.filter((l) => /^[A-Z][a-zA-Z\s]+:/.test(l.trim()));

  // 如果有多行时间戳或多行说话人，使用标准格式解析
  if (timestampLines.length > 1 || speakerLines.length > 1) {
    if (hasTimestamps) {
      return parseWithTimestamps(lines);
    }
    if (hasSpeakers) {
      return parseWithSpeakers(text);
    }
  }

  // 否则使用智能分段（处理只有一行时间戳+大段文本的情况）
  return parseWithSmartSegmentation(text);
}

function parseWithTimestamps(lines: string[]): { segments: TranscriptSegment[]; isTranscript: boolean } {
  const timestampPattern = /^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)$/;
  const speakerPattern = /^([A-Z][a-zA-Z\s]+):\s*(.+)$/;

  const segments: TranscriptSegment[] = [];
  let currentSegment: TranscriptSegment | null = null;
  let inBody = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) continue;

    // 跳过 Markdown 元数据头部
    if (!inBody) {
      if (trimmed.startsWith("#") || trimmed.startsWith(">") || trimmed === "---") {
        continue;
      }
      inBody = true;
    }

    const match = trimmed.match(timestampPattern);

    if (match) {
      // 保存之前的段落
      if (currentSegment) {
        segments.push(currentSegment);
      }

      const time = match[1];
      const rest = match[2];

      const speakerMatch = rest.match(speakerPattern);
      const speaker = speakerMatch ? speakerMatch[1].trim() : null;
      const segmentText = speakerMatch ? speakerMatch[2].trim() : rest;

      currentSegment = {
        id: `seg-${segments.length}`,
        time,
        speaker,
        text: segmentText,
      };
    } else if (currentSegment) {
      // 检查当前行是否是新说话人（无时间戳）
      const speakerMatch = trimmed.match(speakerPattern);
      if (speakerMatch && !trimmed.startsWith("[")) {
        // 保存之前的段落
        segments.push(currentSegment);
        currentSegment = {
          id: `seg-${segments.length}`,
          time: currentSegment.time,
          speaker: speakerMatch[1].trim(),
          text: speakerMatch[2].trim(),
        };
      } else {
        // 继续当前段落
        currentSegment.text += " " + trimmed;
      }
    }
  }

  if (currentSegment) {
    segments.push(currentSegment);
  }

  return { segments, isTranscript: segments.length > 0 };
}

function parseWithSpeakers(text: string): { segments: TranscriptSegment[]; isTranscript: boolean } {
  const speakerPattern = /^([A-Z][a-zA-Z\s]+):\s*(.+)$/m;
  const segments: TranscriptSegment[] = [];

  // 按说话人分割
  const parts = text.split(/(?=^[A-Z][a-zA-Z\s]+:)/m).filter((p) => p.trim());

  parts.forEach((part, i) => {
    const match = part.match(speakerPattern);
    if (match) {
      segments.push({
        id: `seg-${i}`,
        time: "",
        speaker: match[1].trim(),
        text: match[2].trim(),
      });
    } else if (segments.length > 0) {
      segments[segments.length - 1].text += " " + part.trim();
    }
  });

  return { segments, isTranscript: segments.length > 0 };
}

// 基于文本长度估算时间戳
function estimateTimestamps(
  segments: TranscriptSegment[],
  startTime: string,
  totalDurationSeconds?: number
): TranscriptSegment[] {
  if (segments.length <= 1) return segments;

  // 计算总字数
  const totalWords = segments.reduce((sum, seg) => sum + seg.text.split(/\s+/).length, 0);

  // 解析起始时间
  const startSeconds = parseTimeToSeconds(startTime);

  // 估算总时长（基于平均语速 150 词/分钟 = 2.5 词/秒）
  const estimatedDuration = totalDurationSeconds || (totalWords / 2.5);

  let currentSeconds = startSeconds;

  return segments.map((segment) => {
    const wordCount = segment.text.split(/\s+/).length;
    const segmentDuration = (wordCount / totalWords) * estimatedDuration;

    const timestamp = formatSecondsToTime(Math.round(currentSeconds));
    currentSeconds += segmentDuration;

    return {
      ...segment,
      time: timestamp,
      isEstimated: true,
    };
  });
}

function parseTimeToSeconds(time: string): number {
  const parts = time.split(':').map(Number);
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
}

function formatSecondsToTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function parseWithSmartSegmentation(text: string): { segments: TranscriptSegment[]; isTranscript: boolean } {
  // 移除 Markdown 头部，提取正文和时间戳
  const lines = text.split("\n");
  let inBody = false;
  let bodyText = "";
  let firstTimestamp = "";
  let timestampCount = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    if (!inBody) {
      if (trimmed.startsWith("#") || trimmed.startsWith(">") || trimmed === "---") {
        continue;
      }
      inBody = true;
    }

    // 提取时间戳
    const tsMatch = trimmed.match(/^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)$/);
    if (tsMatch) {
      timestampCount++;
      if (!firstTimestamp) {
        firstTimestamp = tsMatch[1];
        bodyText += tsMatch[2] + " ";
      } else {
        bodyText += trimmed + " ";
      }
    } else {
      bodyText += trimmed + " ";
    }
  }

  bodyText = bodyText.trim();

  if (!bodyText) {
    return { segments: [], isTranscript: false };
  }

  // 对这种叙述性播客转录，使用语义分段而非强行提取说话人
  const segments = semanticSplitText(bodyText, firstTimestamp);

  // 如果只有一个时间戳，为所有段落估算时间戳
  if (timestampCount === 1 && segments.length > 1) {
    const estimatedSegments = estimateTimestamps(segments, firstTimestamp);
    return { segments: estimatedSegments, isTranscript: true };
  }

  return { segments, isTranscript: true };
}

// 说话人识别置信度接口
interface SpeakerDetection {
  name: string;
  index: number;
  confidence: number;
  source: 'strict' | 'intro' | 'dialogue' | 'narrative';
}

const CONFIDENCE_THRESHOLDS = {
  strict: 100,
  intro: 90,
  dialogue: 70,
  narrative: 50,
};

// 分层说话人识别算法
function detectSpeakersWithConfidence(text: string): SpeakerDetection[] {
  const detections: SpeakerDetection[] = [];

  // Layer 1: 严格格式 Name: text
  const strictPattern = /(?:^|[.!?]\s+)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2}):\s+/g;
  const strictMatches = [...text.matchAll(strictPattern)];
  for (const match of strictMatches) {
    const name = match[1].trim();
    if (isValidSpeakerName(name)) {
      detections.push({ name, index: match.index!, confidence: 100, source: 'strict' });
    }
  }

  // Layer 2: 自我介绍模式
  const introPatterns = [
    { pattern: /\b(I['\u2019]m|I am)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b/g, group: 2 as const },
    { pattern: /\bmy name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})/gi, group: 1 as const },
  ];
  for (const { pattern, group } of introPatterns) {
    const matches = [...text.matchAll(pattern)];
    for (const match of matches) {
      const name = match[group]?.trim();
      if (name && isValidSpeakerName(name) && !detections.some(d => d.name === name)) {
        detections.push({ name, index: match.index!, confidence: 90, source: 'intro' });
      }
    }
  }

  return detections.sort((a, b) => a.index - b.index);
}

// 智能说话人分段
function splitBySpeakersSmart(text: string, baseTime: string): TranscriptSegment[] {
  const detections = detectSpeakersWithConfidence(text);
  const segments: TranscriptSegment[] = [];

  // 只使用高置信度的识别结果（>=70）作为分段点
  const highConfidenceDetections = detections.filter(d => d.confidence >= 70);

  if (highConfidenceDetections.length === 0) {
    return splitByParagraphs(text, baseTime);
  }

  let lastIndex = 0;
  for (let i = 0; i < highConfidenceDetections.length; i++) {
    const detection = highConfidenceDetections[i];
    const nextIndex = i < highConfidenceDetections.length - 1
      ? highConfidenceDetections[i + 1].index
      : text.length;

    // 向前扩展到句子开头
    let startIndex = detection.index;
    const prevText = text.slice(0, startIndex);
    const lastSentenceEnd = Math.max(
      prevText.lastIndexOf('. '),
      prevText.lastIndexOf('! '),
      prevText.lastIndexOf('? ')
    );
    if (lastSentenceEnd > 0) {
      startIndex = lastSentenceEnd + 2;
    }

    const segmentText = text.slice(lastIndex, nextIndex).trim();
    if (segmentText.length > 30) {
      segments.push({
        id: `seg-${segments.length}`,
        time: baseTime,
        speaker: detection.name,
        text: segmentText,
        confidence: detection.confidence,
      });
    }
    lastIndex = nextIndex;
  }

  // 处理最后一段
  const lastText = text.slice(lastIndex).trim();
  if (lastText.length > 30) {
    segments.push({
      id: `seg-${segments.length}`,
      time: baseTime,
      speaker: null,
      text: lastText,
    });
  }

  return segments.length > 0 ? segments : splitByParagraphs(text, baseTime);
}

// 语义分段算法 - 针对叙述性播客转录优化
function semanticSplitText(text: string, baseTime: string): TranscriptSegment[] {
  // 首先尝试使用智能说话人分段
  const speakerSegments = splitBySpeakersSmart(text, baseTime);
  if (speakerSegments.length > 1 && speakerSegments.some(s => s.speaker)) {
    return speakerSegments;
  }

  // 回退到基于自我介绍和对话转换的分段
  const segments: TranscriptSegment[] = [];

  // 1. 首先尝试识别主持人/嘉宾自我介绍作为分段点
  const introPatterns = [
    // "I'm Natalie Kittrof, this is the Daily"
    { pattern: /\b(I['\u2019]m|I am)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b/g, type: 'host' as const },
    // "my name is Captain..."
    { pattern: /\bmy name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})/gi, type: 'guest' as const },
  ];

  // 找到所有分段点
  const splitPoints: { index: number; label: string | null; confidence?: number }[] = [];

  for (const { pattern, type } of introPatterns) {
    const matches = [...text.matchAll(pattern)];
    for (const match of matches) {
      const name = type === 'host'
        ? match[2]?.trim()
        : match[1]?.trim();
      if (name && isValidSpeakerName(name)) {
        // 向前找句子开头
        let startIdx = match.index!;
        const prevText = text.slice(0, startIdx);
        const lastSentenceEnd = Math.max(
          prevText.lastIndexOf('. '),
          prevText.lastIndexOf('! '),
          prevText.lastIndexOf('? ')
        );
        if (lastSentenceEnd > 0) {
          startIdx = lastSentenceEnd + 2;
        }
        splitPoints.push({ index: startIdx, label: name, confidence: 90 });
      }
    }
  }

  // 2. 识别对话转换点 - "Can you hear me?" "Yeah" 等问答转换
  const dialogueTransitions = [
    /(?:^|[.!?]\s+)(Can you hear me\?|Okay[,\.]? great|Thank you so much|just to start|can you introduce yourself)/gi,
    /(?:^|[.!?]\s+)(Yeah[,\.]?|Yes[,\.]?|No[,\.]?|Okay[,\.]?|Sure[,\.]?|Right[,\.]?)\s+(I can|my name is|I['\u2019]m|I think|I feel|I was|we have|it['\u2019]s|that['\u2019]s)/gi,
  ];

  for (const pattern of dialogueTransitions) {
    const matches = [...text.matchAll(pattern)];
    for (const match of matches) {
      const idx = match.index! + (match[0].match(/^[.!?]\s+/) ? 2 : 0);
      if (!splitPoints.some(p => Math.abs(p.index - idx) < 50)) {
        splitPoints.push({ index: idx, label: null });
      }
    }
  }

  // 按位置排序
  splitPoints.sort((a, b) => a.index - b.index);

  // 去重（距离太近的点合并）
  const uniquePoints: typeof splitPoints = [];
  for (const point of splitPoints) {
    if (uniquePoints.length === 0 || point.index - uniquePoints[uniquePoints.length - 1].index > 100) {
      uniquePoints.push(point);
    }
  }

  // 3. 如果没有找到足够的分段点，使用自然段落分段
  if (uniquePoints.length < 2) {
    return splitByParagraphs(text, baseTime);
  }

  // 4. 根据分段点切分文本
  let lastIndex = 0;
  for (let i = 0; i < uniquePoints.length; i++) {
    const point = uniquePoints[i];
    const nextIndex = i < uniquePoints.length - 1 ? uniquePoints[i + 1].index : text.length;

    const segmentText = text.slice(lastIndex, nextIndex).trim();
    if (segmentText.length > 30) {
      segments.push({
        id: `seg-${segments.length}`,
        time: baseTime,
        speaker: point.label,
        text: segmentText,
        confidence: point.confidence,
      });
    }
    lastIndex = nextIndex;
  }

  // 处理最后一段
  const lastText = text.slice(lastIndex).trim();
  if (lastText.length > 30) {
    segments.push({
      id: `seg-${segments.length}`,
      time: baseTime,
      speaker: null,
      text: lastText,
    });
  }

  return segments.length > 0 ? segments : splitByParagraphs(text, baseTime);
}

// 按自然段落分段（当无法识别说话人时使用）
function splitByParagraphs(text: string, baseTime: string): TranscriptSegment[] {
  const segments: TranscriptSegment[] = [];

  // 按句子结束符分割，然后合并成合适长度的段落
  const sentencePattern = /[^.!?。！？]+[.!?。！？]+/g;
  const sentences = text.match(sentencePattern) || [text];

  let currentText = "";
  const targetLength = 400; // 每段目标长度
  const minLength = 200;    // 最小长度

  for (const sentence of sentences) {
    if (currentText.length + sentence.length > targetLength && currentText.length > minLength) {
      segments.push({
        id: `seg-${segments.length}`,
        time: baseTime,
        speaker: null,
        text: currentText.trim(),
      });
      currentText = sentence;
    } else {
      currentText += sentence;
    }
  }

  if (currentText.trim()) {
    segments.push({
      id: `seg-${segments.length}`,
      time: baseTime,
      speaker: null,
      text: currentText.trim(),
    });
  }

  return segments;
}

// 验证说话人名字是否有效（排除常见误匹配）
function isValidSpeakerName(name: string): boolean {
  if (!name || name.length < 2) return false;

  const invalidNames = new Set([
    // 代词
    'I', 'It', 'He', 'She', 'We', 'They', 'You', 'My', 'The', 'A', 'An',
    'This', 'That', 'These', 'Those', 'His', 'Her', 'Its', 'Our', 'Their',
    // 连词/介词
    'And', 'But', 'Or', 'Nor', 'For', 'Yet', 'So', 'If', 'Then', 'Than',
    'As', 'At', 'By', 'In', 'On', 'To', 'Of', 'Up', 'Via', 'Per',
    'From', 'With', 'Into', 'Onto', 'Upon', 'Over', 'Under', 'Above',
    // 形容词
    'New', 'Old', 'Good', 'Bad', 'Big', 'Small', 'Long', 'Short',
    'One', 'Two', 'Three', 'First', 'Second', 'Last', 'Next', 'Every',
    'All', 'Some', 'Any', 'Many', 'Much', 'More', 'Most', 'Other',
    'Such', 'Only', 'Own', 'Same', 'Few', 'Little', 'Less', 'Least',
    'Very', 'Just', 'Now', 'Here', 'There', 'Then',
    // 时间
    'Today', 'Friday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Saturday', 'Sunday',
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December',
    // 地名/国籍
    'American', 'Indian', 'Chinese', 'Japanese', 'British', 'Persian',
    // 媒体/机构
    'Daily', 'Times', 'York',
    // 称谓（单独出现时）
    'Mr', 'Mrs', 'Ms', 'Dr',
    // 疑问词
    'What', 'When', 'Where', 'Why', 'How', 'Who', 'Which', 'Whose',
    // 常见动词开头
    'Have', 'Has', 'Had', 'Do', 'Does', 'Did', 'Is', 'Are', 'Was', 'Were',
    'Can', 'Could', 'Will', 'Would', 'Shall', 'Should', 'May', 'Might',
    'Must', 'Need', 'Dare', 'Used', 'Ought',
  ]);

  const words = name.split(/\s+/);

  // 如果所有单词都在无效列表中，则无效
  if (words.every(w => invalidNames.has(w))) return false;

  // 如果第一个单词是常见的无效词且只有一个单词，则无效
  if (words.length === 1 && invalidNames.has(words[0])) return false;

  // 检查是否包含数字（人名通常不包含数字）
  if (/\d/.test(name)) return false;

  // 检查是否全大写（可能是缩写而非人名）
  if (name === name.toUpperCase() && name.length > 3) return false;

  return true;
}

// ============================================
// 工具函数
// ============================================

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightText(text: string, keyword: string): string {
  if (!keyword.trim()) return text;
  const escaped = escapeRegex(keyword);
  return text.replace(new RegExp(`(${escaped})`, "gi"), '<mark class="transcript-mark">$1</mark>');
}

// 说话人颜色分配
function getSpeakerColors(speakers: (string | null)[]): Map<string, string> {
  const uniqueSpeakers = [...new Set(speakers.filter(Boolean))];
  const colors = [
    "#6366f1", // indigo
    "#10b981", // emerald
    "#f59e0b", // amber
    "#ec4899", // pink
    "#06b6d4", // cyan
    "#8b5cf6", // violet
    "#f97316", // orange
    "#14b8a6", // teal
  ];

  const map = new Map<string, string>();
  uniqueSpeakers.forEach((speaker, i) => {
    if (speaker) {
      map.set(speaker, colors[i % colors.length]);
    }
  });
  return map;
}

// 滚动位置存储
const SCROLL_STORAGE_KEY = "transcript_scroll_positions";

function saveScrollPosition(fileId: string, position: number) {
  try {
    const data = JSON.parse(localStorage.getItem(SCROLL_STORAGE_KEY) || "{}");
    data[fileId] = position;
    localStorage.setItem(SCROLL_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
}

function getScrollPosition(fileId: string): number {
  try {
    const data = JSON.parse(localStorage.getItem(SCROLL_STORAGE_KEY) || "{}");
    return data[fileId] || 0;
  } catch {
    return 0;
  }
}

// ============================================
// 主组件
// ============================================

export default function TranscriptContent({
  content,
  searchKeyword = "",
  onScrollProgress,
  fileId,
  onSegmentsChange,
  onCurrentSegmentChange,
  onContainerRef,
}: TranscriptContentProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { settings } = useReader();
  const [hoveredSegment, setHoveredSegment] = useState<string | null>(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [showScrollToTop, setShowScrollToTop] = useState(false);
  const [currentSegment, setCurrentSegment] = useState<TranscriptSegment | null>(null);

  const { segments, isTranscript } = useMemo(() => {
    return parseTranscript(content);
  }, [content]);

  // 通知父组件 segments 变化
  useEffect(() => {
    onSegmentsChange?.(segments);
  }, [segments, onSegmentsChange]);

  const speakerColors = useMemo(() => {
    return getSpeakerColors(segments.map((s) => s.speaker));
  }, [segments]);

  // 检查是否所有时间戳都相同（如都是 00:00）
  const allSameTime = useMemo(() => {
    if (segments.length <= 1) return false;
    const firstTime = segments[0].time;
    if (!firstTime) return false;
    return segments.every((s) => s.time === firstTime);
  }, [segments]);

  // 是否显示时间戳列
  // 当存在时间戳且不是全部为空时显示
  // 即使所有时间戳相同（如都是00:00），也显示第一个作为参考
  const showTimeColumn = useMemo(() => {
    const hasAnyTime = segments.some((s) => s.time);
    return hasAnyTime;
  }, [segments]);

  // 恢复滚动位置
  useEffect(() => {
    if (!containerRef.current || !fileId) return;
    const savedPosition = getScrollPosition(fileId);
    if (savedPosition > 0) {
      containerRef.current.scrollTop = savedPosition;
    }
  }, [fileId]);

  // 通知父组件容器引用
  useEffect(() => {
    if (containerRef.current) {
      onContainerRef?.(containerRef.current);
    }
    return () => onContainerRef?.(null);
  }, [onContainerRef]);

  // 滚动监听
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let rafId: number;
    let lastScrollTop = 0;
    let isScrolling = false;
    let scrollTimeout: ReturnType<typeof setTimeout>;

    const updateScrollState = () => {
      const scrollTop = container.scrollTop;
      const scrollHeight = container.scrollHeight - container.clientHeight;
      const progress = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
      const roundedProgress = Math.round(progress);

      setScrollProgress(roundedProgress);
      setShowScrollToTop(scrollTop > 300);

      if (onScrollProgress) {
        onScrollProgress(roundedProgress);
      }

      // 检测当前可见段落
      const segmentElements = container.querySelectorAll('[data-segment-id]');
      let closestSegmentId: string | null = null;
      let closestDistance = Infinity;

      segmentElements.forEach((el) => {
        const rect = el.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const distance = Math.abs(rect.top - containerRect.top - 100);

        if (distance < closestDistance && rect.top < containerRect.bottom && rect.bottom > containerRect.top) {
          closestDistance = distance;
          closestSegmentId = el.getAttribute('data-segment-id');
        }
      });

      if (closestSegmentId) {
        const closestSegment = segments.find(s => s.id === closestSegmentId) || null;
        if (closestSegment && closestSegment.id !== currentSegment?.id) {
          setCurrentSegment(closestSegment);
          onCurrentSegmentChange?.(closestSegment);
        }
      }

      // 保存滚动位置（节流）
      if (fileId && Math.abs(scrollTop - lastScrollTop) > 50) {
        saveScrollPosition(fileId, scrollTop);
        lastScrollTop = scrollTop;
      }
    };

    const handleScroll = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        updateScrollState();
        rafId = 0;
      });
    };

    // 处理鼠标滚轮事件，实现平滑滚动状态检测
    const handleWheel = (e: WheelEvent) => {
      isScrolling = true;
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        isScrolling = false;
      }, 150);

      // 检测是否滚动到底部或顶部边缘
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      const isAtTop = scrollTop <= 10;

      // 如果滚动到底部且继续向下滚动，阻止默认行为（防止页面滚动）
      if (isAtBottom && e.deltaY > 0) {
        e.preventDefault();
      }
      // 如果滚动到顶部且继续向上滚动，阻止默认行为
      if (isAtTop && e.deltaY < 0) {
        e.preventDefault();
      }
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    container.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      container.removeEventListener("scroll", handleScroll);
      container.removeEventListener("wheel", handleWheel);
      if (rafId) cancelAnimationFrame(rafId);
      clearTimeout(scrollTimeout);
    };
  }, [onScrollProgress, fileId]);

  // 滚动速度系数
  const scrollMultiplier = useMemo(() => {
    const multipliers: Record<string, number> = {
      slow: 0.5,
      normal: 1,
      fast: 2,
    };
    return multipliers[settings.scrollSpeed] || 1;
  }, [settings.scrollSpeed]);

  // 键盘导航
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!container) return;

      const lineHeight = 24 * scrollMultiplier;
      const pageHeight = (container.clientHeight - lineHeight * 2) * scrollMultiplier;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          container.scrollBy({ top: lineHeight, behavior: "smooth" });
          break;
        case "ArrowUp":
          e.preventDefault();
          container.scrollBy({ top: -lineHeight, behavior: "smooth" });
          break;
        case "PageDown":
          e.preventDefault();
          container.scrollBy({ top: pageHeight, behavior: "smooth" });
          break;
        case "PageUp":
          e.preventDefault();
          container.scrollBy({ top: -pageHeight, behavior: "smooth" });
          break;
        case "Home":
          e.preventDefault();
          container.scrollTo({ top: 0, behavior: "smooth" });
          break;
        case "End":
          e.preventDefault();
          container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
          break;
      }
    };

    container.addEventListener("keydown", handleKeyDown);
    container.setAttribute("tabindex", "0");
    return () => container.removeEventListener("keydown", handleKeyDown);
  }, [scrollMultiplier]);

  const handleTimeClick = useCallback((time: string) => {
    console.log(`Seek to: ${time}`);
  }, []);

  const scrollToTop = useCallback(() => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const renderSegmentText = (text: string) => {
    if (!searchKeyword.trim()) return text;
    const html = highlightText(text, searchKeyword);
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="relative flex-1 flex flex-col overflow-hidden min-h-0">
      {/* 滚动进度条 */}
      <div className="absolute top-0 left-0 right-0 h-[3px] z-10" style={{ background: "var(--reader-border)" }}>
        <div
          className="h-full transition-all duration-150 ease-out"
          style={{
            width: `${scrollProgress}%`,
            background: "var(--reader-accent)",
            boxShadow: "0 0 6px var(--reader-accent)",
          }}
        />
      </div>

      {/* 内容区域 */}
      <div
        ref={containerRef}
        className="reader-scroll flex-1 overflow-y-auto outline-none min-h-0"
        style={{ background: "var(--reader-bg)" }}
      >
        <div className="max-w-[800px] mx-auto py-8 px-4 sm:px-6 md:px-8">
          {/* 转录段落 */}
          {isTranscript && segments.length > 0 ? (
            <div className="space-y-1">
              {segments.map((segment) => {
                const speakerColor = segment.speaker
                  ? speakerColors.get(segment.speaker) || "var(--reader-text-secondary)"
                  : null;

                return (
                  <div
                    key={segment.id}
                    data-segment-id={segment.id}
                    className="group flex gap-3 sm:gap-5 py-3 px-3 sm:px-4 rounded-xl transition-all duration-200"
                    style={{
                      background:
                        hoveredSegment === segment.id
                          ? "var(--reader-hover)"
                          : "transparent",
                    }}
                    onMouseEnter={() => setHoveredSegment(segment.id)}
                    onMouseLeave={() => setHoveredSegment(null)}
                  >
                    {/* 时间戳 */}
                    {showTimeColumn && (
                      <div className="flex-shrink-0 w-[52px] sm:w-[60px] pt-1">
                        {segment.time && (
                          <button
                            onClick={() => handleTimeClick(segment.time)}
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-mono font-medium transition-all duration-200 hover:scale-105 cursor-pointer group/time ${
                              segment.isEstimated ? 'opacity-60' : ''
                            }`}
                            style={{
                              background: segment.isEstimated
                                ? "rgba(99, 102, 241, 0.05)"
                                : "rgba(99, 102, 241, 0.1)",
                              color: "var(--reader-accent)",
                              border: segment.isEstimated
                                ? "1px dashed rgba(99, 102, 241, 0.2)"
                                : "1px solid rgba(99, 102, 241, 0.2)",
                            }}
                            title={segment.isEstimated ? `估算时间: ${segment.time}` : `跳转到 ${segment.time}`}
                          >
                            <Play className="w-2.5 h-2.5 opacity-0 group-hover/time:opacity-100 transition-opacity" />
                            <span className="group-hover/time:hidden">{segment.time}</span>
                            <span className="hidden group-hover/time:inline">{segment.isEstimated ? '估算' : '播放'}</span>
                          </button>
                        )}
                      </div>
                    )}

                    {/* 内容 */}
                    <div className="flex-1 min-w-0">
                      {/* 说话人 */}
                      {segment.speaker && (
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <div
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: speakerColor || "var(--reader-text-secondary)" }}
                          />
                          <User className="w-3 h-3" style={{ color: speakerColor || undefined }} />
                          <span
                            className="text-[13px] font-semibold"
                            style={{ color: speakerColor || "var(--reader-text)" }}
                          >
                            {segment.speaker}
                          </span>
                          {/* 置信度指示器 */}
                          {segment.confidence && segment.confidence < 90 && (
                            <span
                              className="text-[10px] px-1 py-0.5 rounded"
                              style={{
                                background: 'rgba(234, 179, 8, 0.2)',
                                color: '#eab308',
                              }}
                              title="说话人识别置信度"
                            >
                              {segment.confidence}%
                            </span>
                          )}
                        </div>
                      )}

                      {/* 文本 */}
                      <p
                        className="text-[15px] sm:text-base leading-relaxed"
                        style={{
                          color: "var(--reader-text)",
                          opacity: 0.9,
                          lineHeight: "var(--reader-line-height, 1.8)",
                        }}
                      >
                        {renderSegmentText(segment.text)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* 纯文本回退 */
            <div className="reader-content">
              {segments.map((segment) => (
                <p
                  key={segment.id}
                  className="mb-4"
                  dangerouslySetInnerHTML={{
                    __html: highlightText(segment.text, searchKeyword),
                  }}
                />
              ))}
            </div>
          )}

          {/* 空状态 */}
          {segments.length === 0 && (
            <div className="text-center py-16">
              <p style={{ color: "var(--reader-text-secondary)" }}>暂无内容</p>
            </div>
          )}

          {/* 底部间距 */}
          <div className="h-8" />
        </div>
      </div>

      {/* 回到顶部按钮 */}
      {showScrollToTop && (
        <button
          onClick={scrollToTop}
          className="absolute bottom-6 right-6 w-11 h-11 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-110 z-20"
          style={{
            background: "var(--reader-accent)",
            color: "#ffffff",
            boxShadow: "0 4px 12px rgba(99, 102, 241, 0.4)",
          }}
          title="回到顶部"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="18 15 12 9 6 15" />
          </svg>
        </button>
      )}

      {/* 搜索高亮样式 */}
      <style>{`
        .transcript-mark {
          background: var(--reader-mark);
          color: var(--reader-text);
          padding: 1px 2px;
          border-radius: 2px;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}

export { parseTranscript };
