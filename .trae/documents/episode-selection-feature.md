# 播客搜索结果集数选择功能 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为播客搜索结果添加集数选择功能，用户可浏览播客的所有单集列表，预览单集信息，并选择特定单集进行下载。

**Architecture:**
- 后端新增 `/api/episodes/` 路由，通过 RSS URL 解析获取单集列表
- 前端搜索页面每个播客卡片添加"查看单集"按钮，点击展开单集列表
- 单集列表支持排序、分页、预览，可直接选择下载

**Tech Stack:** FastAPI, Next.js 16, React 19, TypeScript, Tailwind CSS, Framer Motion, feedparser

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/routers/episodes.py` | 新建 | 集数列表 API：解析 RSS 返回单集列表 |
| `backend/main.py` | 修改 | 注册 episodes 路由 |
| `backend/services/podcast_search.py` | 修改 | PodcastIndexClient 添加获取单集列表方法 |
| `web-dashboard/src/lib/api.ts` | 修改 | 前端 API：添加集数列表接口类型和函数 |
| `web-dashboard/src/app/dashboard/search/page.tsx` | 修改 | 搜索页面：添加集数选择交互 |
| `web-dashboard/src/components/EpisodeList.tsx` | 新建 | 集数列表组件：展示、排序、分页、下载 |

---

## 现有能力分析

### 后端已有能力
- `AudioDownloader.parse_rss()` — 可解析 RSS 获取完整单集列表（含标题、时长、发布日期、描述等）
- `PodcastFeed` / `PodcastEpisode` 模型 — 已包含所需字段
- PodcastIndex API — 支持搜索播客，返回 RSS URL

### 前端已有能力
- 搜索页面 — 已展示播客列表，有下载按钮
- API 客户端 — 已封装 fetch 逻辑
- 设计系统 — 深色主题、卡片式布局、Framer Motion 动画

---

## Task 1: 后端 — 新增集数列表 API

### 1.1 创建 `episodes.py` 路由

**文件:** `backend/routers/episodes.py` (新建)

**步骤:**

- [ ] **Step 1: 创建路由文件和请求/响应模型**

```python
"""Episodes router for podcast episode listing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.audio_downloader import AudioDownloader
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


class EpisodeItem(BaseModel):
    """单集列表项模型."""

    index: int                    # 在列表中的序号（用于下载）
    title: str
    description: str | None = None
    duration_seconds: int | None = None
    duration_formatted: str | None = None
    publish_date: str | None = None  # ISO 格式日期字符串
    episode_number: int | None = None
    audio_url: str | None = None


class EpisodesResponse(BaseModel):
    """集数列表响应模型."""

    podcast_title: str
    podcast_description: str | None = None
    podcast_image: str | None = None
    total_episodes: int
    episodes: list[EpisodeItem]


class EpisodesRequest(BaseModel):
    """集数列表请求模型."""

    rss_url: str
    sort: str = "newest"  # "newest" | "oldest"
    page: int = 1
    page_size: int = 20
```

- [ ] **Step 2: 实现集数列表获取接口**

```python
def _format_duration(seconds: int | None) -> str | None:
    """格式化秒数为可读字符串."""
    if not seconds:
        return None
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


@router.post("/", response_model=EpisodesResponse)
async def get_episodes(request: EpisodesRequest):
    """获取播客单集列表.

    通过 RSS URL 解析获取播客的所有单集信息。

    Args:
        request: 包含 RSS URL、排序方式和分页参数

    Returns:
        播客信息和单集列表
    """
    try:
        downloader = AudioDownloader()
        feed = downloader.parse_rss(request.rss_url)

        # 排序
        episodes = feed.episodes
        if request.sort == "newest":
            episodes = sorted(
                episodes,
                key=lambda ep: ep.publish_date or datetime.min,
                reverse=True,
            )
        elif request.sort == "oldest":
            episodes = sorted(
                episodes,
                key=lambda ep: ep.publish_date or datetime.max,
                reverse=False,
            )

        total = len(episodes)

        # 分页
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        paged_episodes = episodes[start:end]

        # 构建响应
        episode_items = []
        for idx, ep in enumerate(paged_episodes, start=start + 1):
            episode_items.append(
                EpisodeItem(
                    index=idx,
                    title=ep.title,
                    description=ep.description[:200] + "..." if ep.description and len(ep.description) > 200 else ep.description,
                    duration_seconds=ep.duration_seconds,
                    duration_formatted=_format_duration(ep.duration_seconds),
                    publish_date=ep.publish_date.isoformat() if ep.publish_date else None,
                    episode_number=ep.episode_number,
                    audio_url=str(ep.audio_url) if ep.audio_url else None,
                )
            )

        return EpisodesResponse(
            podcast_title=feed.title,
            podcast_description=feed.description,
            podcast_image=None,  # feedparser 可能不直接提供图片
            total_episodes=total,
            episodes=episode_items,
        )

    except Exception as e:
        logger.error("获取集数列表失败", error=str(e), rss_url=request.rss_url)
        raise HTTPException(status_code=500, detail=f"获取集数列表失败: {str(e)}")
```

### 1.2 注册路由

**文件:** `backend/main.py`

- [ ] **Step 3: 导入并注册 episodes 路由**

在现有导入中添加：
```python
from backend.routers import health, search, process, transcribe, download, images, episodes
```

在 `app.include_router` 部分添加：
```python
app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"])
```

---

## Task 2: 前端 — 添加集数列表 API 类型和函数

**文件:** `web-dashboard/src/lib/api.ts`

- [ ] **Step 4: 添加集数列表类型和 API 函数**

在文件末尾（Image Generation 部分之后）添加：

```typescript
// Episodes
export interface EpisodeItem {
  index: number;
  title: string;
  description?: string;
  duration_seconds?: number;
  duration_formatted?: string;
  publish_date?: string;
  episode_number?: number;
  audio_url?: string;
}

export interface EpisodesResponse {
  podcast_title: string;
  podcast_description?: string;
  podcast_image?: string;
  total_episodes: number;
  episodes: EpisodeItem[];
}

export interface EpisodesRequest {
  rss_url: string;
  sort?: "newest" | "oldest";
  page?: number;
  page_size?: number;
}

export async function getEpisodes(
  request: EpisodesRequest
): Promise<EpisodesResponse> {
  return fetchApi<EpisodesResponse>("/api/episodes/", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
```

---

## Task 3: 前端 — 创建集数列表组件

**文件:** `web-dashboard/src/components/EpisodeList.tsx` (新建)

- [ ] **Step 5: 创建 EpisodeList 组件**

```tsx
"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock,
  Calendar,
  Download,
  Loader2,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  Headphones,
  X,
} from "lucide-react";
import { getEpisodes, EpisodeItem, startDownload, getDownloadStatus } from "@/lib/api";

interface EpisodeListProps {
  rssUrl: string;
  podcastTitle: string;
  onClose: () => void;
}

export default function EpisodeList({ rssUrl, podcastTitle, onClose }: EpisodeListProps) {
  const [episodes, setEpisodes] = useState<EpisodeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);
  const [totalEpisodes, setTotalEpisodes] = useState(0);
  const [downloadingIndex, setDownloadingIndex] = useState<number | null>(null);
  const pageSize = 20;

  useEffect(() => {
    loadEpisodes();
  }, [rssUrl, sort, page]);

  const loadEpisodes = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getEpisodes({
        rss_url: rssUrl,
        sort,
        page,
        page_size: pageSize,
      });
      setEpisodes(data.episodes);
      setTotalEpisodes(data.total_episodes);
    } catch (err) {
      setError("加载单集列表失败");
      console.error("Load episodes error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (episode: EpisodeItem) => {
    setDownloadingIndex(episode.index);
    try {
      const response = await startDownload({
        rss_url: rssUrl,
        episode_index: episode.index,
      });

      // Poll status
      const pollInterval = setInterval(async () => {
        try {
          const status = await getDownloadStatus(response.task_id);
          if (status.status === "completed" || status.status === "failed") {
            clearInterval(pollInterval);
            setDownloadingIndex(null);
          }
        } catch {
          clearInterval(pollInterval);
          setDownloadingIndex(null);
        }
      }, 2000);

      setTimeout(() => {
        clearInterval(pollInterval);
        setDownloadingIndex(null);
      }, 60000);
    } catch (err) {
      setDownloadingIndex(null);
      setError("下载失败");
    }
  };

  const totalPages = Math.ceil(totalEpisodes / pageSize);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-4 border-t border-white/[0.06] pt-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-medium text-white">单集列表</h4>
          <p className="text-xs text-gray-500 mt-0.5">
            共 {totalEpisodes} 集
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setSort(sort === "newest" ? "oldest" : "newest");
              setPage(1);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-400 hover:bg-white/10 transition"
          >
            <ArrowUpDown className="w-3 h-3" />
            {sort === "newest" ? "最新优先" : "最早优先"}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white/[0.02] rounded-xl p-4 animate-pulse">
              <div className="h-3 bg-white/5 rounded w-2/3 mb-2" />
              <div className="h-2 bg-white/5 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : (
        <>
          {/* Episode List */}
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {episodes.map((episode) => (
              <motion.div
                key={episode.index}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.04] rounded-xl p-3.5 transition group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Headphones className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h5 className="text-sm text-white font-medium truncate">
                      {episode.title}
                    </h5>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-500">
                      {episode.duration_formatted && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {episode.duration_formatted}
                        </span>
                      )}
                      {episode.publish_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(episode.publish_date).toLocaleDateString("zh-CN")}
                        </span>
                      )}
                      {episode.episode_number && (
                        <span>第 {episode.episode_number} 期</span>
                      )}
                    </div>
                    {episode.description && (
                      <p className="text-[11px] text-gray-600 mt-1.5 line-clamp-2">
                        {episode.description}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDownload(episode)}
                    disabled={downloadingIndex === episode.index}
                    className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition disabled:opacity-50 flex-shrink-0"
                    title="下载该单集"
                  >
                    {downloadingIndex === episode.index ? (
                      <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/[0.04]">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-400 hover:bg-white/10 transition disabled:opacity-30"
              >
                上一页
              </button>
              <span className="text-xs text-gray-500">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-400 hover:bg-white/10 transition disabled:opacity-30"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
```

---

## Task 4: 前端 — 修改搜索页面添加集数选择交互

**文件:** `web-dashboard/src/app/dashboard/search/page.tsx`

- [ ] **Step 6: 导入 EpisodeList 组件并添加展开状态**

在现有导入中添加：
```typescript
import EpisodeList from "@/components/EpisodeList";
import { ListMusic } from "lucide-react";
```

在组件 state 中添加：
```typescript
const [expandedPodcastId, setExpandedPodcastId] = useState<string | null>(null);
```

- [ ] **Step 7: 在播客卡片上添加"查看单集"按钮**

在下载按钮旁边添加查看单集按钮（在下载按钮的 `</button>` 之后，`<ArrowRight` 之前）：

```tsx
<button
  onClick={(e) => {
    e.stopPropagation();
    setExpandedPodcastId(
      expandedPodcastId === podcast.id ? null : podcast.id
    );
  }}
  className={`p-2 rounded-xl transition ${
    expandedPodcastId === podcast.id
      ? "bg-white/10 text-white"
      : "bg-white/5 hover:bg-white/10 text-gray-400"
  }`}
  title="查看单集列表"
>
  <ListMusic className="w-4 h-4" />
</button>
```

- [ ] **Step 8: 在卡片下方条件渲染 EpisodeList**

在结果卡片的闭合 `</motion.div>` 之前（在内部 `</div>` 之后）添加：

```tsx
<AnimatePresence>
  {expandedPodcastId === podcast.id && (
    <EpisodeList
      rssUrl={podcast.rss_url}
      podcastTitle={podcast.title}
      onClose={() => setExpandedPodcastId(null)}
    />
  )}
</AnimatePresence>
```

注意：由于 EpisodeList 使用了 `motion.div` 的 `height: "auto"` 动画，需要确保父容器能够正确展开。

---

## Task 5: 构建和测试

- [ ] **Step 9: 运行前端构建**

```bash
cd d:\podcast_notes\web-dashboard
npm run build
```

- [ ] **Step 10: 验证后端路由**

启动后端服务：
```bash
cd d:\podcast_notes
python -m backend.main
```

测试集数列表 API：
```bash
python -c "
import urllib.request, json
req = urllib.request.Request(
    'http://localhost:8000/api/episodes/',
    data=json.dumps({'rss_url': 'https://feeds.fountain.fm/rtxhHb8dvHH0DuRU9TVJ', 'sort': 'newest', 'page': 1, 'page_size': 5}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
r = urllib.request.urlopen(req)
data = json.loads(r.read())
print('Podcast:', data['podcast_title'])
print('Total:', data['total_episodes'])
for ep in data['episodes']:
    print(f'  {ep[\"index\"]}. {ep[\"title\"]} ({ep.get(\"duration_formatted\", \"unknown\")})')
"
```

- [ ] **Step 11: 浏览器端验证**

1. 打开 Dashboard 搜索页面，搜索播客
2. 点击"查看单集列表"按钮（列表图标）
3. 确认单集列表正确展开，显示标题、时长、日期
4. 测试排序切换（最新/最早）
5. 测试分页功能
6. 测试下载特定单集

---

## 数据流说明

### 获取单集列表流程

```
用户点击"查看单集"按钮
  → 前端调用 POST /api/episodes/
    → 后端 AudioDownloader.parse_rss(rss_url)
      → feedparser 解析 RSS XML
        → 返回 PodcastFeed（含 episodes 列表）
    → 后端排序、分页
    → 返回 EpisodesResponse
  → 前端渲染 EpisodeList 组件
    → 展示单集卡片（标题、时长、日期、描述）
    → 提供排序、分页、下载操作
```

### 下载特定单集流程

```
用户在单集列表中点击下载按钮
  → 前端调用 POST /api/download/
    → 后端 download_from_rss(rss_url, episode_index)
      → 解析 RSS，按索引选择单集
      → 下载音频文件
    → 返回 DownloadResponse
  → 前端轮询下载状态
```

---

## UI/UX 设计说明

### 交互设计

1. **展开/收起**：点击列表图标展开单集列表，再次点击或点击 X 收起
2. **排序**：默认按最新优先，可切换为最早优先
3. **分页**：每页 20 条，超出显示分页控件
4. **下载**：每个单集卡片右侧有下载按钮，点击后显示加载动画

### 视觉设计

- 单集列表在播客卡片内部展开，使用 `border-t` 与上方内容分隔
- 单集卡片使用更 subtle 的背景色（`bg-white/[0.02]`）区分层级
- 时长、日期使用 `text-[10px]` 小字展示
- 描述文字使用 `line-clamp-2` 限制两行

### 响应式适配

- 桌面端：单集卡片横向布局（图标 + 信息 + 下载按钮）
- 移动端：保持相同布局，文字自动截断
- 分页控件在小屏幕上保持可用

---

## 开发排期（敏捷迭代）

### Sprint 1（当前）— MVP 核心功能
- [x] 后端集数列表 API
- [x] 前端集数列表组件
- [x] 搜索页面集成
- [x] 排序与分页

### Sprint 2 — 体验优化
- [ ] 添加单集搜索/过滤功能
- [ ] 添加收藏功能（本地存储）
- [ ] 播放历史记录

### Sprint 3 — 高级功能
- [ ] 批量下载
- [ ] 分享功能
- [ ] 性能优化（虚拟滚动处理大量单集）
