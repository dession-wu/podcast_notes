/**
 * 转录任务 localStorage 持久化.
 *
 * 任务的轮询状态（进行中/已完成/失败）在刷新页面后仍可恢复，
 * key 结构为 Record<fileId, TranscriptionTask>。
 */

const STORAGE_KEY = "podcast_transcription_tasks";

export interface TranscriptionTask {
  /** 音频文件 ID（作为持久化主键） */
  fileId: string;
  /** 后端转录任务 ID */
  taskId: string;
  /** pending | processing | completed | failed */
  status: string;
  /** 0-100 */
  progress: number;
  stage?: string | null;
  result: {
    text: string;
    word_count: number;
    segment_count?: number;
    language: string | null;
    duration_seconds?: number | null;
    engine_used?: string | null;
    language_detected?: string | null;
    detection_method?: string | null;
  } | null;
  error: string | null;
  errorCategory: string | null;
  errorDetail?: string | null;
  estimate: {
    total_seconds: number;
    formatted_time: string;
    provider?: string;
    audio_duration_seconds?: number;
    audio_duration_formatted?: string;
    speed_factor?: number;
    has_cuda?: boolean;
  } | null;
  elapsedSeconds: number | null;
  remainingSeconds: number | null;
}

/** 读取全部已持久化的转录任务（fileId → task） */
export function getStoredTranscriptionTasks(): Record<string, TranscriptionTask> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, TranscriptionTask>;
    }
    return {};
  } catch (err) {
    console.error("读取转录任务持久化数据失败:", err);
    return {};
  }
}

/** 写入单条转录任务（以 task.fileId 为主键，已存在则覆盖） */
export function saveTranscriptionTask(task: TranscriptionTask): void {
  if (typeof window === "undefined") return;
  try {
    const stored = getStoredTranscriptionTasks();
    stored[task.fileId] = task;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch (err) {
    console.error("保存转录任务失败:", err);
  }
}

/** 按 fileId 更新已持久化的转录任务 */
export function updateTranscriptionTask(fileId: string, task: TranscriptionTask): void {
  if (typeof window === "undefined") return;
  try {
    const stored = getStoredTranscriptionTasks();
    stored[fileId] = task;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch (err) {
    console.error("更新转录任务失败:", err);
  }
}

/** 删除单条转录任务 */
export function removeTranscriptionTask(fileId: string): void {
  if (typeof window === "undefined") return;
  try {
    const stored = getStoredTranscriptionTasks();
    delete stored[fileId];
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch (err) {
    console.error("删除转录任务失败:", err);
  }
}

/** 清空全部转录任务 */
export function clearTranscriptionTasks(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.error("清空转录任务失败:", err);
  }
}