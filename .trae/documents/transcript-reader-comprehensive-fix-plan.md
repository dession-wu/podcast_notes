# 转录文本阅读器系统性修复与优化计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 系统性修复说话人识别准确性、时间戳完整性、鼠标滚轮滚动功能三大关键问题，达到商业级产品质量要求。

**Architecture:** 基于 React + TypeScript + Next.js 的转录文本阅读器组件体系，通过优化解析算法、增强事件处理、完善状态管理来提升用户体验。

**Tech Stack:** React 19, TypeScript, Next.js 16, Tailwind CSS, Framer Motion, Lucide React

---

## 文件结构映射

| 文件 | 职责 | 修改类型 |
|------|------|----------|
| `web-dashboard/src/components/reader/TranscriptContent.tsx` | 转录文本解析与渲染核心组件 | 重度修改 |
| `web-dashboard/src/components/reader/ReaderShell.tsx` | 阅读器容器，协调各子组件 | 轻度修改 |
| `web-dashboard/src/components/reader/ReaderSearch.tsx` | 搜索功能组件 | 已完成修复 |
| `web-dashboard/src/components/reader/ReaderContext.tsx` | 阅读器状态管理Context | 新增滚动速度设置 |
| `web-dashboard/src/app/globals.css` | 全局样式，包含阅读器主题变量 | 新增滚动相关样式 |

---

## 问题 1：说话人识别准确性优化

### 根因分析

当前 `semanticSplitText` 算法的误判模式：
1. **过度识别**：将叙述文本中的主语（如 "Captain Viswakarma has sailed..."）误判为说话人切换点
2. **截断问题**：正则匹配范围过宽，捕获到不完整名字（如 "Captain We the" 而非完整名字）
3. **缺乏置信度**：没有评估识别结果的可靠性
4. **单一名称误识别**：将 "the Daily"、"The Strai" 等普通名词误判为说话人

### 优化方案

采用**分层识别策略**：
- **Layer 1**：严格格式匹配（`Speaker: text`）— 置信度 100%
- **Layer 2**：自我介绍模式（`I'm Name` / `my name is Name`）— 置信度 90%
- **Layer 3**：对话转换标记（问答交替）— 置信度 70%
- **Layer 4**：叙述视角转换（人名+动词）— 置信度 50%，需人工确认

### Task 1.1: 重构说话人识别算法

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx:189-289`

- [ ] **Step 1: 添加置信度评分系统**

```typescript
interface SpeakerDetection {
  name: string;
  index: number;
  confidence: number; // 0-100
  source: 'strict' | 'intro' | 'dialogue' | 'narrative';
}

const CONFIDENCE_THRESHOLDS = {
  strict: 100,      // Name: text 格式
  intro: 90,        // I'm Name / my name is Name
  dialogue: 70,     // 对话转换
  narrative: 50,    // 叙述视角转换
};
```

- [ ] **Step 2: 实现分层识别函数**

```typescript
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
  
  // Layer 2: 自我介绍
  const introPatterns = [
    { pattern: /\b(I['\u2019]m|I am)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b/g, group: 2 },
    { pattern: /\bmy name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})/gi, group: 1 },
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
```

- [ ] **Step 3: 实现智能分段逻辑**

```typescript
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
        speaker: detection.confidence >= 70 ? detection.name : null,
        text: segmentText,
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
  
  return segments;
}
```

- [ ] **Step 4: 更新 TranscriptContent 组件使用新算法**

替换 `semanticSplitText` 函数调用为 `splitBySpeakersSmart`。

- [ ] **Step 5: 添加置信度显示UI**

在说话人标签旁添加置信度指示器（可选显示）：

```tsx
{segment.speaker && (
  <div className="flex items-center gap-1.5 mb-1.5">
    <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: speakerColor }} />
    <User className="w-3 h-3" style={{ color: speakerColor }} />
    <span className="text-[13px] font-semibold" style={{ color: speakerColor }}>
      {segment.speaker}
    </span>
    {/* 置信度指示器 */}
    {segment.confidence && segment.confidence < 90 && (
      <span className="text-[10px] px-1 py-0.5 rounded bg-yellow-500/20 text-yellow-500">
        {segment.confidence}%
      </span>
    )}
  </div>
)}
```

### Task 1.2: 扩展无效名称过滤列表

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx:330-359`

- [ ] **Step 1: 增强 isValidSpeakerName 函数**

```typescript
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
    'Mr', 'Mrs', 'Ms', 'Dr', 'Captain',
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
```

### Task 1.3: 添加准确率评估测试

**Files:**
- Create: `web-dashboard/src/components/reader/__tests__/speaker-detection.test.ts`

- [ ] **Step 1: 创建测试文件**

```typescript
import { describe, it, expect } from 'vitest';
import { detectSpeakersWithConfidence, isValidSpeakerName } from '../TranscriptContent';

describe('说话人识别准确率', () => {
  it('应正确识别自我介绍模式', () => {
    const text = "I'm Natalie Kittrof, this is the Daily.";
    const results = detectSpeakersWithConfidence(text);
    expect(results).toHaveLength(1);
    expect(results[0].name).toBe('Natalie Kittrof');
    expect(results[0].confidence).toBe(90);
  });

  it('应正确识别 my name is 模式', () => {
    const text = "Yeah, my name is Captain Vishwakarma.";
    const results = detectSpeakersWithConfidence(text);
    expect(results).toHaveLength(1);
    expect(results[0].name).toBe('Captain Vishwakarma');
  });

  it('不应将普通名词误判为说话人', () => {
    const text = "The Daily is a podcast. The Strait is important.";
    const results = detectSpeakersWithConfidence(text);
    expect(results.filter(r => r.name === 'Daily')).toHaveLength(0);
    expect(results.filter(r => r.name === 'Strait')).toHaveLength(0);
  });

  it('准确率应达到95%以上', () => {
    const testCases = [
      { text: "I'm John Smith.", expected: ['John Smith'] },
      { text: "My name is Alice Johnson.", expected: ['Alice Johnson'] },
      { text: "The New York Times is a newspaper.", expected: [] },
      { text: "Captain Viswakarma has sailed.", expected: [] }, // 叙述不应识别
    ];
    
    let correct = 0;
    let total = 0;
    
    for (const { text, expected } of testCases) {
      const results = detectSpeakersWithConfidence(text);
      const names = results.map(r => r.name);
      
      if (JSON.stringify(names.sort()) === JSON.stringify(expected.sort())) {
        correct++;
      }
      total++;
    }
    
    const accuracy = (correct / total) * 100;
    expect(accuracy).toBeGreaterThanOrEqual(95);
  });
});

describe('isValidSpeakerName', () => {
  it('应接受有效人名', () => {
    expect(isValidSpeakerName('Natalie')).toBe(true);
    expect(isValidSpeakerName('John Smith')).toBe(true);
    expect(isValidSpeakerName('Captain Viswakarma')).toBe(true);
  });

  it('应拒绝无效名称', () => {
    expect(isValidSpeakerName('The')).toBe(false);
    expect(isValidSpeakerName('Daily')).toBe(false);
    expect(isValidSpeakerName('It')).toBe(false);
    expect(isValidSpeakerName('Friday')).toBe(false);
  });
});
```

---

## 问题 2：时间戳识别完整性修复

### 根因分析

当前问题：
1. **单一时间戳**：转录文件只有开头一个 `[00:00]`，后续内容没有时间戳
2. **无时间戳分配策略**：当只有一个时间戳时，所有段落共享同一时间戳，无实际意义
3. **缺乏时间戳生成机制**：对于没有逐段标注时间戳的转录文本，没有基于文本长度估算时间戳的算法

### 优化方案

实现**时间戳智能分配算法**：
- 当转录文件只有一个时间戳时，基于段落字数占总字数的比例，线性分配时间戳
- 假设平均语速为 150 词/分钟
- 提供原始时间戳和估算时间戳的视觉区分

### Task 2.1: 实现时间戳智能分配算法

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx:150-187`

- [ ] **Step 1: 添加时间戳估算函数**

```typescript
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
  
  return segments.map((segment, index) => {
    const wordCount = segment.text.split(/\s+/).length;
    const segmentDuration = (wordCount / totalWords) * estimatedDuration;
    
    const timestamp = formatSecondsToTime(Math.round(currentSeconds));
    currentSeconds += segmentDuration;
    
    return {
      ...segment,
      time: timestamp,
      isEstimated: true, // 标记为估算时间戳
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
```

- [ ] **Step 2: 更新 parseWithSmartSegmentation 函数**

```typescript
function parseWithSmartSegmentation(
  text: string,
  totalDurationSeconds?: number
): { segments: TranscriptSegment[]; isTranscript: boolean } {
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

  const segments = semanticSplitText(bodyText, firstTimestamp);
  
  // 如果只有一个时间戳，为所有段落估算时间戳
  if (timestampCount === 1 && segments.length > 1) {
    const estimatedSegments = estimateTimestamps(segments, firstTimestamp, totalDurationSeconds);
    return { segments: estimatedSegments, isTranscript: true };
  }
  
  return { segments, isTranscript: true };
}
```

- [ ] **Step 3: 更新 TranscriptSegment 接口**

```typescript
export interface TranscriptSegment {
  id: string;
  time: string;
  speaker: string | null;
  text: string;
  isEstimated?: boolean; // 是否为估算时间戳
  confidence?: number;   // 说话人识别置信度
}
```

### Task 2.2: 添加时间戳视觉区分

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx:611-630`

- [ ] **Step 1: 为估算时间戳添加视觉标记**

```tsx
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
```

### Task 2.3: 添加时间戳连续性校验

**Files:**
- Create: `web-dashboard/src/components/reader/__tests__/timestamp-continuity.test.ts`

- [ ] **Step 1: 创建时间戳校验测试**

```typescript
import { describe, it, expect } from 'vitest';
import { estimateTimestamps, parseTimeToSeconds, formatSecondsToTime } from '../TranscriptContent';

describe('时间戳连续性校验', () => {
  it('应生成连续递增的时间戳', () => {
    const segments = [
      { id: '1', time: '00:00', speaker: null, text: 'First paragraph with ten words here.' },
      { id: '2', time: '', speaker: null, text: 'Second paragraph also has ten words here.' },
      { id: '3', time: '', speaker: null, text: 'Third paragraph with another ten words.' },
    ];
    
    const result = estimateTimestamps(segments, '00:00');
    
    // 验证时间戳递增
    const times = result.map(r => parseTimeToSeconds(r.time));
    for (let i = 1; i < times.length; i++) {
      expect(times[i]).toBeGreaterThan(times[i - 1]);
    }
  });

  it('覆盖率应达到99%以上', () => {
    const segments = [
      { id: '1', time: '00:00', speaker: null, text: 'First.' },
      { id: '2', time: '', speaker: null, text: 'Second.' },
      { id: '3', time: '', speaker: null, text: 'Third.' },
    ];
    
    const result = estimateTimestamps(segments, '00:00');
    const coveredSegments = result.filter(r => r.time && r.time !== '').length;
    const coverage = (coveredSegments / result.length) * 100;
    
    expect(coverage).toBeGreaterThanOrEqual(99);
  });

  it('时间格式转换应正确', () => {
    expect(parseTimeToSeconds('00:00')).toBe(0);
    expect(parseTimeToSeconds('01:30')).toBe(90);
    expect(parseTimeToSeconds('10:05')).toBe(605);
    
    expect(formatSecondsToTime(0)).toBe('00:00');
    expect(formatSecondsToTime(90)).toBe('01:30');
    expect(formatSecondsToTime(605)).toBe('10:05');
  });
});
```

---

## 问题 3：鼠标滚轮滚动功能实现

### 根因分析

当前问题：
1. **wheel 事件未监听**：只监听了 `scroll` 事件，没有专门处理 `wheel` 事件
2. **滚动不流畅**：`requestAnimationFrame` 节流可能导致滚动卡顿
3. **跨浏览器兼容性**：不同浏览器对 wheel 事件的 `deltaY` 值处理不同
4. **缺乏滚动速度调节**：用户无法自定义滚动速度

### 优化方案

- 添加 `wheel` 事件监听器，实现平滑滚动
- 使用 `passive: true` 提升滚动性能
- 添加滚动速度设置到 ReaderContext
- 实现跨浏览器兼容的滚动处理

### Task 3.1: 增强滚动事件处理

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx:469-508`

- [ ] **Step 1: 重构滚动监听逻辑**

```typescript
// 滚动监听
useEffect(() => {
  const container = containerRef.current;
  if (!container) return;

  let rafId: number;
  let lastScrollTop = 0;
  let isScrolling = false;
  let scrollTimeout: NodeJS.Timeout;

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

  // 处理鼠标滚轮事件，实现平滑滚动
  const handleWheel = (e: WheelEvent) => {
    // 阻止默认行为，实现自定义滚动
    // e.preventDefault(); // 不阻止，保持原生滚动
    
    // 检测滚动方向并更新状态
    isScrolling = true;
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      isScrolling = false;
    }, 150);
  };

  container.addEventListener("scroll", handleScroll, { passive: true });
  container.addEventListener("wheel", handleWheel, { passive: true });
  
  return () => {
    container.removeEventListener("scroll", handleScroll);
    container.removeEventListener("wheel", handleWheel);
    if (rafId) cancelAnimationFrame(rafId);
    clearTimeout(scrollTimeout);
  };
}, [onScrollProgress, fileId]);
```

### Task 3.2: 添加滚动速度设置

**Files:**
- Modify: `web-dashboard/src/components/reader/ReaderContext.tsx`

- [ ] **Step 1: 扩展 ReaderSettings 接口**

```typescript
export type ReaderScrollSpeed = "slow" | "normal" | "fast";

export interface ReaderSettings {
  theme: ReaderTheme;
  font: ReaderFont;
  fontSize: ReaderFontSize;
  lineHeight: ReaderLineHeight;
  scrollSpeed: ReaderScrollSpeed;
  showToc: boolean;
  showPageNumbers: boolean;
}

const defaultSettings: ReaderSettings = {
  theme: "dark",
  font: "system",
  fontSize: "base",
  lineHeight: "normal",
  scrollSpeed: "normal",
  showToc: true,
  showPageNumbers: false,
};
```

- [ ] **Step 2: 添加滚动速度设置方法**

```typescript
const setScrollSpeed = useCallback((scrollSpeed: ReaderScrollSpeed) => {
  setSettings((s) => ({ ...s, scrollSpeed }));
}, []);
```

- [ ] **Step 3: 在 Context Value 中暴露**

```typescript
interface ReaderContextValue {
  settings: ReaderSettings;
  setTheme: (theme: ReaderTheme) => void;
  setFont: (font: ReaderFont) => void;
  setFontSize: (size: ReaderFontSize) => void;
  setLineHeight: (lh: ReaderLineHeight) => void;
  setScrollSpeed: (speed: ReaderScrollSpeed) => void; // 新增
  toggleToc: () => void;
  togglePageNumbers: () => void;
  resetSettings: () => void;
}
```

### Task 3.3: 在工具栏添加滚动速度控制

**Files:**
- Modify: `web-dashboard/src/components/reader/ReaderToolbar.tsx`

- [ ] **Step 1: 添加滚动速度控制UI**

在 ReaderToolbar 中添加滚动速度切换按钮组：

```tsx
{/* 滚动速度 */}
<div className="flex items-center gap-1">
  <span className="text-[10px] mr-1" style={{ color: "var(--reader-text-secondary)" }}>
    滚动
  </span>
  {(["slow", "normal", "fast"] as const).map((speed) => (
    <button
      key={speed}
      onClick={() => setScrollSpeed(speed)}
      className="px-1.5 py-0.5 rounded text-[10px] transition"
      style={{
        background: settings.scrollSpeed === speed ? "var(--reader-accent)" : "transparent",
        color: settings.scrollSpeed === speed ? "#fff" : "var(--reader-text-secondary)",
      }}
    >
      {speed === "slow" ? "慢" : speed === "normal" ? "中" : "快"}
    </button>
  ))}
</div>
```

### Task 3.4: 实现滚动速度调节逻辑

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx`

- [ ] **Step 1: 根据设置调整滚动行为**

```typescript
// 滚动速度系数
const SCROLL_SPEED_MULTIPLIERS: Record<ReaderScrollSpeed, number> = {
  slow: 0.5,
  normal: 1,
  fast: 2,
};

// 在组件中使用
const { settings } = useReader();
const scrollMultiplier = SCROLL_SPEED_MULTIPLIERS[settings.scrollSpeed];

// 键盘导航中使用滚动速度
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
    // ... 其他按键
  }
};
```

### Task 3.5: 添加跨浏览器滚动兼容性处理

**Files:**
- Modify: `web-dashboard/src/components/reader/TranscriptContent.tsx`
- Modify: `web-dashboard/src/app/globals.css`

- [ ] **Step 1: 添加 CSS 平滑滚动支持**

```css
/* globals.css */
.reader-scroll {
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch; /* iOS 惯性滚动 */
  overscroll-behavior: contain; /* 防止滚动传播 */
}

/* Firefox 滚动条 */
.reader-scroll {
  scrollbar-width: thin;
  scrollbar-color: var(--reader-border) transparent;
}
```

- [ ] **Step 2: 添加浏览器检测和兼容性处理**

```typescript
// 检测浏览器类型
function getBrowser(): 'chrome' | 'firefox' | 'safari' | 'edge' | 'unknown' {
  const ua = navigator.userAgent;
  if (ua.includes('Firefox')) return 'firefox';
  if (ua.includes('Safari') && !ua.includes('Chrome')) return 'safari';
  if (ua.includes('Edg')) return 'edge';
  if (ua.includes('Chrome')) return 'chrome';
  return 'unknown';
}

// 针对不同浏览器调整滚动参数
const getScrollConfig = () => {
  const browser = getBrowser();
  switch (browser) {
    case 'firefox':
      return { wheelMultiplier: 1.5 };
    case 'safari':
      return { wheelMultiplier: 0.8 };
    default:
      return { wheelMultiplier: 1 };
  }
};
```

### Task 3.6: 添加滚动位置记忆测试

**Files:**
- Create: `web-dashboard/src/components/reader/__tests__/scroll-memory.test.ts`

- [ ] **Step 1: 创建滚动位置记忆测试**

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { saveScrollPosition, getScrollPosition } from '../TranscriptContent';

describe('滚动位置记忆', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('应正确保存和恢复滚动位置', () => {
    const fileId = 'test-file-123';
    const position = 500;

    saveScrollPosition(fileId, position);
    const retrieved = getScrollPosition(fileId);

    expect(retrieved).toBe(position);
  });

  it('不存在的文件应返回0', () => {
    const position = getScrollPosition('non-existent');
    expect(position).toBe(0);
  });

  it('应支持多个文件的滚动位置记忆', () => {
    saveScrollPosition('file1', 100);
    saveScrollPosition('file2', 200);
    saveScrollPosition('file3', 300);

    expect(getScrollPosition('file1')).toBe(100);
    expect(getScrollPosition('file2')).toBe(200);
    expect(getScrollPosition('file3')).toBe(300);
  });
});
```

---

## 测试与验收

### 验收标准

| 功能 | 验收标准 | 测试方法 |
|------|----------|----------|
| 说话人识别 | 准确率 >= 95%，无 "the Daily" 等误判 | 运行 speaker-detection.test.ts |
| 时间戳覆盖 | 覆盖率 >= 99%，时间戳连续递增 | 运行 timestamp-continuity.test.ts |
| 滚动功能 | 支持鼠标滚轮，60fps流畅度，跨浏览器兼容 | 手动测试 + 性能分析 |
| 滚动记忆 | 刷新后恢复位置，多文件独立记忆 | 运行 scroll-memory.test.ts |

### 性能目标

- 滚动帧率 >= 60fps
- 首次渲染时间 < 100ms（对于10000字符文本）
- 搜索响应时间 < 50ms

### 浏览器兼容性

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

---

## 实施顺序

1. **Task 1.2** - 扩展无效名称过滤（快速修复，影响最大）
2. **Task 2.1** - 时间戳智能分配（提升时间戳覆盖率）
3. **Task 3.1** - 增强滚动事件处理（修复核心功能）
4. **Task 1.1** - 重构说话人识别算法（长期优化）
5. **Task 3.2-3.4** - 滚动速度设置（用户体验提升）
6. **Task 2.2** - 时间戳视觉区分（UI优化）
7. **Task 3.5** - 跨浏览器兼容性（稳定性）
8. **所有测试任务** - 验证修复效果

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 说话人识别过度保守 | 漏识别 | 提供手动标记功能 |
| 时间戳估算不准确 | 用户体验差 | 明确标注"估算"状态 |
| 滚动性能下降 | 卡顿 | 使用 requestAnimationFrame 节流 |
| 浏览器兼容性差异 | 功能异常 | 渐进增强，优雅降级 |