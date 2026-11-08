/**
 * 后端 API 客户端 — 与 FastAPI 路由一一对应.
 *
 * - 基址: 默认走 Next.js rewrites 代理（相对路径 /api），
 *   也可通过 NEXT_PUBLIC_API_URL 直连后端。
 * - 鉴权: 若配置了 NEXT_PUBLIC_API_KEY，则所有请求携带 X-API-Key 头，
 *   与后端 ApiKeyMiddleware（X-API-Key / Bearer）保持兼容。
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

// Persist only a SHA-256 fingerprint and random operation ID, never transcripts or Keys.
// Reusing identical inputs after a timeout, reload or explicit retry returns the saved
// operation. The server decides whether any real LLM call needs a trial reservation.
const operationIds = new Map<string, string>();
function newOperationId(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(20)), value => value.toString(16).padStart(2, "0")).join("");
}
async function operationId(path: string, options: RequestInit): Promise<string> {
  if (options.body && typeof options.body !== "string") return newOperationId();
  const input = `${options.method || "GET"}\n${path}\n${options.body || ""}`;
  // HTTP-only local previews lack SubtleCrypto; retain retry IDs in memory only.
  if (!crypto.subtle) {
    const id = operationIds.get(input) || newOperationId();
    operationIds.set(input, id);
    return id;
  }
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  const fingerprint = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("");
  const key = `podcast-llm-operation:${fingerprint}`;
  let id = operationIds.get(key);
  try { id ||= sessionStorage.getItem(key) || undefined; } catch { /* private mode */ }
  id ||= newOperationId();
  operationIds.set(key, id);
  try { sessionStorage.setItem(key, id); } catch { /* memory fallback */ }
  return id;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(!(options.body instanceof FormData) ? {"Content-Type": "application/json"} : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }

  headers["X-LLM-Operation-ID"] ||= await operationId(path, options);

  let res: Response;
  try { res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  }); } catch {
    throw new ApiError("连接中断。请重试同一操作；若已生成，服务器会返回原结果，不重复扣次。", 0);
  }

  if (!res.ok) {
    let detail = `请求失败（HTTP ${res.status}）`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : (body.detail.message || JSON.stringify(body.detail));
      }
    } catch {
      /* 响应体不是 JSON 时使用默认错误信息 */
    }
    if ([401, 402, 403, 409, 503].includes(res.status) && /AI|模型|额度|Key|操作/.test(detail)) {
      detail += " 可在「个人服务设置 → 管理我的 AI 模型」查看额度、配置或验证个人 Key。";
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<T>;
}

/* ==================== 类型定义 ==================== */

/** 播客搜索结果项 */
export interface PodcastResult {
  id: string;
  title: string;
  author: string;
  description: string;
  episode_count: number;
  rss_url: string;
  image_url: string;
  website: string;
}

/** 搜索响应 */
export interface SearchResponse {
  success: boolean;
  results: PodcastResult[];
  count: number;
  source: string;
}

/** 单集列表项 */
export interface EpisodeItem {
  index: number;
  title: string;
  description: string | null;
  duration_seconds: number | null;
  duration_formatted: string | null;
  publish_date: string | null;
  episode_number: number | null;
  audio_url: string | null;
}

/** 单集列表响应 */
export interface EpisodesResponse {
  podcast_title: string;
  podcast_description: string | null;
  podcast_image: string | null;
  total_episodes: number;
  episodes: EpisodeItem[];
}

/** 下载任务创建响应 */
export interface DownloadResponse {
  task_id: string;
  status: string;
}

/** 下载任务结果 */
export interface DownloadResult {
  file_path: string;
  file_name: string;
  file_size_mb: number;
  episode_title: string;
  podcast_name: string;
  duration_seconds: number | null;
}

/** 下载任务状态响应 */
export interface DownloadStatusResponse {
  task_id: string;
  status: string;
  progress: number | null;
  downloaded_bytes: number | null;
  total_bytes: number | null;
  result: DownloadResult | null;
  error: string | null;
  error_category: string | null;
}

/** 下载历史条目 */
export interface DownloadHistoryItem {
  task_id: string;
  status: string;
  progress: number;
  episode_title: string;
  podcast_name: string;
  file_size_mb: number | null;
  created_at: string;
  error: string | null;
  error_category: string | null;
}

/** 下载历史响应 */
export interface DownloadHistoryResponse {
  history: DownloadHistoryItem[];
}

/** 打开文件夹响应 */
export interface OpenFolderResponse {
  success: boolean;
  message: string;
  file_path: string | null;
}

/** 文件库条目 */
export interface LibraryFile {
  id: string;
  name: string;
  type: "audio" | "transcript" | "image";
  podcast_name: string;
  episode_title: string;
  size_mb: number;
  created_at: string;
  file_path: string;
  status: string;
}

/** 文件库列表响应 */
export interface LibraryFilesResponse {
  files: LibraryFile[];
  total: number;
  type_counts: Record<string, number>;
}

/** 转录文件内容响应 */
export interface TranscriptContentResponse {
  file_id: string;
  file_name: string;
  content: string;
  word_count: number;
}

/** 生成的笔记 */
export interface GeneratedNote {
  title: string;
  content: string;
  tags: string[];
  word_count: number;
}

/** 模板推荐信息（process 响应内嵌） */
export interface RecommendationInfo {
  was_recommended: boolean;
  reason: string;
  confidence: number;
}

/** 内容处理响应 */
export interface ProcessResponse {
  success: boolean;
  note: GeneratedNote;
  used_template: string;
  recommendation_info: RecommendationInfo | null;
  /** 生成成功后自动保存到笔记库的 id；保存失败时为 null */
  saved_note_id: number | null;
}

/** 内容特征向量 */
export interface ContentFeatures {
  time_line_density: number;
  data_density: number;
  concept_density: number;
  narrative_density: number;
  emotional_density: number;
  text_length: number;
  confidence: number;
}

/** 模板推荐结果 */
export interface TemplateRecommendation {
  recommended_template: string;
  recommended_name: string;
  confidence: number;
  reason: string;
  features: ContentFeatures;
  alternatives: string[];
}

/** 模板分析响应 */
export interface AnalyzeResponse {
  success: boolean;
  recommendation: TemplateRecommendation;
}

/** 图片生成任务结果 */
export interface ImageResult {
  images: { id: string; path: string; name: string; index: number }[];
  count: number;
}

/** 图片生成状态响应 */
export interface ImageStatusResponse {
  task_id: string;
  status: string;
  progress: number | null;
  result: ImageResult | null;
  error: string | null;
}

/** 转录任务结果 */
export interface TranscriptionResult {
  text: string;
  word_count: number;
  segment_count: number;
  language: string | null;
  duration_seconds: number | null;
  engine_used: string | null;
  language_detected: string | null;
  detection_method: string | null;
}

/** 转录任务状态响应 */
export interface TranscriptionEstimate {
  total_seconds: number;
  formatted_time: string;
  provider?: string;
  audio_duration_seconds?: number;
  audio_duration_formatted?: string;
  speed_factor?: number;
  has_cuda?: boolean;
}

export interface TranscribeStatusResponse {
  task_id: string;
  status: string;
  progress: number | null;
  stage: string | null;
  result: TranscriptionResult | null;
  error: string | null;
  error_category: string | null;
  error_detail: string | null;
  estimate: TranscriptionEstimate | null;
  elapsed_seconds: number | null;
  remaining_seconds: number | null;
}

/** 转录任务创建响应 */
export interface TranscribeResponse {
  task_id: string;
  status: string;
  estimate: TranscriptionEstimate | null;
}

/** 下载路径设置响应 */
export interface DownloadPathResponse {
  current_path: string;
  is_custom: boolean;
  default_path: string;
}

/** 路径校验响应 */
export interface PathValidationResponse {
  valid: boolean;
  path: string;
  writable: boolean;
  error: string | null;
}

/* ==================== 搜索 / 单集 ==================== */

/** 搜索播客 */
export async function searchPodcasts(query: string, maxResults?: number): Promise<SearchResponse> {
  return request<SearchResponse>("/api/search/", {
    method: "POST",
    body: JSON.stringify({ term: query, max_results: maxResults }),
  });
}

/** 获取播客单集列表 */
export async function getEpisodes(params: {
  rss_url: string;
  sort?: string;
  page?: number;
  page_size?: number;
}): Promise<EpisodesResponse> {
  return request<EpisodesResponse>("/api/episodes/", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/* ==================== 下载 ==================== */

/** 发起下载任务 */
export async function startDownload(params: {
  rss_url: string;
  episode_index?: number;
}): Promise<DownloadResponse> {
  return request<DownloadResponse>("/api/download/", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** 查询下载任务状态 */
export async function getDownloadStatus(taskId: string): Promise<DownloadStatusResponse> {
  return request<DownloadStatusResponse>(`/api/download/${taskId}`);
}

/** 重试失败的下载任务 */
export async function retryDownload(taskId: string): Promise<DownloadResponse> {
  return request<DownloadResponse>("/api/download/retry", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}

/** 获取下载历史 */
export async function getDownloadHistory(limit = 20): Promise<DownloadHistoryResponse> {
  return request<DownloadHistoryResponse>(`/api/download/history/list?limit=${limit}`);
}

/** 打开下载文件所在文件夹 */
export async function openDownloadFolder(taskId: string): Promise<OpenFolderResponse> {
  return request<OpenFolderResponse>(`/api/download/open-folder/${taskId}`, {
    method: "POST",
  });
}

/* ==================== 文件库 ==================== */

/** 获取文件库文件列表 */
export async function getLibraryFiles(
  type: string = "all",
  search: string = "",
  sort: string = "time_desc",
  timeRange: string = "all"
): Promise<LibraryFilesResponse> {
  const params = new URLSearchParams({ type, search, sort, time_range: timeRange });
  return request<LibraryFilesResponse>(`/api/library/files?${params.toString()}`);
}

/** 读取转录文件内容 */
export async function getTranscriptContent(fileId: string): Promise<TranscriptContentResponse> {
  return request<TranscriptContentResponse>(`/api/library/transcript-content/${encodeURIComponent(fileId)}`);
}

export function openLibraryLocation(filePath: string) {
  return request<{success: boolean; message: string}>("/api/library/open-file", {
    method: "POST", body: JSON.stringify({file_path: filePath}),
  });
}

export function uploadAudio(audio: File) {
  const body = new FormData();
  body.append("audio", audio);
  return request<TranscribeResponse>("/api/transcribe/", {method: "POST", body});
}

export interface ApplicationSettings {
  llm_provider: string;
  stt_engine: string;
  configured: Record<string, boolean>;
}

export function getApplicationSettings() {
  return request<ApplicationSettings>("/api/settings/application");
}

export function saveApplicationSettings(data: Record<string, string>) {
  return request<ApplicationSettings>("/api/settings/application", {
    method: "PUT", body: JSON.stringify(data),
  });
}

/** 删除文件库文件 */
export interface DeleteFileResponse {
  success: boolean;
  message: string;
  file_name: string;
}

export async function deleteLibraryFile(filePath: string): Promise<DeleteFileResponse> {
  return request<DeleteFileResponse>("/api/library/files", {
    method: "DELETE",
    body: JSON.stringify({ file_path: filePath }),
  });
}

/* ==================== 内容处理 / 模板 ==================== */

/** 处理转录文本生成笔记 */
export async function processContent(params: {
  transcript_text: string;
  template?: string;
  podcast_name?: string;
  episode_title?: string;
  allow_auto_recommend?: boolean;
}): Promise<ProcessResponse> {
  return request<ProcessResponse>("/api/process/", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** 分析转录文本并推荐模板 */
export async function analyzeContent(params: {
  transcript_text: string;
  podcast_name?: string;
  episode_title?: string;
}): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/analyze/", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/* ==================== 图片生成 ==================== */

/** 发起图片生成任务 */
export async function startImageGeneration(params: {
  title: string;
  content: string;
  tags?: string[];
  podcast_name?: string;
  episode_title?: string;
  style?: string;
  template?: string;
}): Promise<DownloadResponse> {
  return request<DownloadResponse>("/api/images/", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** 查询图片生成任务状态 */
export async function getImageStatus(taskId: string): Promise<ImageStatusResponse> {
  return request<ImageStatusResponse>(`/api/images/${taskId}`);
}

/* ==================== 转录 ==================== */

/** 按文件路径发起转录任务 */
export async function startTranscriptionByPath(
  filePath: string,
  forceEngine?: string
): Promise<TranscribeResponse> {
  return request<TranscribeResponse>("/api/transcribe/by-path", {
    method: "POST",
    body: JSON.stringify({ file_path: filePath, force_engine: forceEngine }),
  });
}

/** 查询转录任务状态 */
export async function getTranscriptionStatus(taskId: string): Promise<TranscribeStatusResponse> {
  return request<TranscribeStatusResponse>(`/api/transcribe/${taskId}`);
}

/* ==================== 下载路径设置 ==================== */

/** 获取当前下载路径设置 */
export async function getDownloadSettings(): Promise<DownloadPathResponse> {
  return request<DownloadPathResponse>("/api/settings/download-path");
}

/** 设置自定义下载路径 */
export async function updateDownloadSettings(path: string): Promise<DownloadPathResponse> {
  return request<DownloadPathResponse>("/api/settings/download-path", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

/** 重置为默认下载路径 */
export async function resetDownloadSettings(): Promise<DownloadPathResponse> {
  return request<DownloadPathResponse>("/api/settings/download-path/reset", {
    method: "POST",
  });
}

/** 校验下载路径是否可用 */
export async function validateDownloadPath(path: string): Promise<PathValidationResponse> {
  return request<PathValidationResponse>("/api/settings/download-path/validate", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

/* ==================== 笔记库 ==================== */

/** 笔记列表项（不含正文，列表接口返回） */
export interface NoteSummary {
  id: number;
  title: string;
  tags: string[];
  word_count: number;
  template: string;
  podcast_name: string;
  episode_title: string;
  episode_id: number | null;
  created_at: string;
  updated_at: string;
}

/** 笔记详情（含正文与转录摘要） */
export interface NoteDetail extends NoteSummary {
  content: string;
  transcript_text: string | null;
}

/** 笔记列表响应 */
export interface NotesListResponse {
  items: NoteSummary[];
  total: number;
  limit: number;
  offset: number;
}

/** 单条笔记响应 */
export interface NoteResponse {
  note: NoteDetail;
}

/** 删除笔记响应 */
export interface NoteDeleteResponse {
  deleted: boolean;
  note_id: number;
}

/** 保存笔记响应（幂等保存接口） */
export interface NoteSaveResponse {
  note: NoteDetail;
}

/** 获取笔记列表（分页，倒序） */
export async function listNotes(limit = 50, offset = 0): Promise<NotesListResponse> {
  return request<NotesListResponse>(`/api/notes/?limit=${limit}&offset=${offset}`);
}

/** 获取笔记详情 */
export async function getNote(noteId: number): Promise<NoteResponse> {
  return request<NoteResponse>(`/api/notes/${noteId}`);
}

/** 手动保存一条笔记（生成流程会自动入库，此接口供补充场景使用） */
export async function saveNote(note: {
  title: string;
  content: string;
  tags: string[];
  word_count: number;
  template: string;
  podcast_name?: string | null;
  episode_title?: string | null;
  episode_id?: number | null;
  transcript_text?: string | null;
}): Promise<NoteSaveResponse> {
  return request<NoteSaveResponse>("/api/notes/", {
    method: "POST",
    body: JSON.stringify(note),
  });
}

/** 删除笔记 */
export async function deleteNote(noteId: number): Promise<NoteDeleteResponse> {
  return request<NoteDeleteResponse>(`/api/notes/${noteId}`, { method: "DELETE" });
}

/** 笔记关联图片（note_images 表记录） */
export interface NoteImage {
  id: number;
  note_id: number;
  image_path: string;
  image_name: string;
  created_at: string;
  /** 静态访问 URL（/images/{image_name}） */
  url: string;
}

/** 笔记图片列表响应 */
export interface NoteImagesResponse {
  success: boolean;
  images: NoteImage[];
  count: number;
}

/** 获取笔记关联图片列表 */
export async function getNoteImages(noteId: number): Promise<NoteImagesResponse> {
  return request<NoteImagesResponse>(`/api/notes/${noteId}/images`);
}

/** 为笔记生成配图（标题/内容作素材），返回生成并已写入关联的图片列表 */
export async function generateNoteImages(noteId: number, style?: string): Promise<NoteImagesResponse> {
  return request<NoteImagesResponse>(`/api/notes/${noteId}/images`, {
    method: "POST",
    ...(style ? { body: JSON.stringify({ style }) } : {}),
  });
}

/**
 * 下载导出笔记（md / txt）。
 * 导出接口返回文件流而非 JSON，故不走 request<T>，使用 fetch + blob 触发浏览器下载。
 */
export async function downloadNoteExport(noteId: number, format: "md" | "txt"): Promise<void> {
  const headers: Record<string, string> = {};
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  const response = await fetch(`${API_BASE_URL}/api/notes/${noteId}/export?format=${format}`, {
    headers,
  });
  if (!response.ok) {
    throw new Error(`导出失败（${response.status}）`);
  }
  /* 从响应头解析文件名，解析失败时使用兜底名 */
  const disposition = response.headers.get("Content-Disposition") ?? "";
  let filename = `note-${noteId}.${format}`;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    filename = decodeURIComponent(utf8Match[1].trim());
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
