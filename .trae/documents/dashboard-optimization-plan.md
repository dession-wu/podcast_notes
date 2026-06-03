# Dashboard 系统性优化升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 Dashboard 信息架构，消除功能冗余，新增文件管理模块，提升用户体验与工作效率。

**Architecture:** 重构导航结构（5项核心导航），新增「文件库」页面统一管理下载/转录/生成内容，后端新增文件扫描 API，前端实现分类筛选、搜索、排序。

**Tech Stack:** FastAPI, React/Next.js, Tailwind CSS, Framer Motion, Lucide React

---

## 当前问题诊断

### 1. 功能冗余
- **首页 (Dashboard)**：显示「最近下载」「最近转录」统计卡片
- **Downloads 页面**：独立的下载任务列表（仅前端状态，刷新丢失）
- **Search 页面**：自带 DownloadManager 侧边栏显示下载任务
- **问题**：三个地方展示同类内容，数据不互通，Downloads 页面数据不持久

### 2. 文件管理缺失
- 下载的音频文件、转录的文本文件、生成的图片分散在各页面
- 无统一入口查看所有已产出文件
- 无法按类型/时间/关键词查找历史文件
- 刷新页面后任务列表清空（前端状态未持久化）

### 3. 导航臃肿
- 8个导航项，其中 Publish 为纯静态假数据
- 用户核心路径（搜索→下载→转录→生成）被分散在多个页面

---

## 优化方案

### Phase 1: 信息架构重构（导航整合）

**新导航结构（5项）：**

| 导航项 | 图标 | 内容 | 说明 |
|--------|------|------|------|
| 概览 | LayoutDashboard | 原 Dashboard 首页，保留统计与快捷入口 | 移除「最近下载/转录」列表，改为跳转链接 |
| 播客搜索 | Search | 原 Search 页面 | 保留，移除 DownloadManager 侧边栏（移至文件库） |
| 文件库 | FolderOpen | **新增** — 统一管理所有文件 | 下载音频、转录文本、生成图片的分类管理 |
| 内容创作 | Sparkles | 原 Content + Images 合并 | 转录文本输入 + AI笔记生成 + 图片生成 |
| 系统设置 | Settings | 原 Settings 页面 | 保留，增加存储路径设置 |

**删除/合并：**
- Downloads 页面 → 合并入「文件库」
- Transcripts 页面 → 合并入「文件库」（上传入口移至文件库）
- Images 页面 → 合并入「内容创作」
- Publish 页面 → 隐藏（未实现功能不应占位）

### Phase 2: 文件库模块（核心新增）

**页面路径**: `/dashboard/library`

**功能设计：**

1. **分类标签页**：
   - 「全部」— 所有文件类型
   - 「音频」— 已下载的播客音频
   - 「转录」— 已转录的文本文件
   - 「图片」— 已生成的小红书图片

2. **筛选与搜索栏**：
   - 关键词搜索（文件名、播客名称、单集标题模糊匹配）
   - 时间筛选：今天/本周/本月/全部
   - 排序：时间倒序/时间正序/名称/大小

3. **文件列表视图**：
   - 列表模式：文件名、类型图标、播客名称、大小、创建时间、操作按钮
   - 操作按钮：打开位置、播放（音频）、查看（转录/图片）、删除

4. **空状态**：
   - 根据当前分类显示对应引导（如「暂无转录文件，前往播客搜索下载音频」）

**后端 API 设计：**

```
GET /api/library/files?type=all|audio|transcript|image&search=&sort=time_desc&time_range=all
Response: {
  files: [
    {
      id: string,
      name: string,
      type: "audio" | "transcript" | "image",
      podcast_name: string,
      episode_title: string,
      size_mb: number,
      created_at: string,
      file_path: string,
      status: "completed" | "processing" | "error"
    }
  ]
}
```

实现方式：扫描 `data/audio/`、`data/transcripts/`、`data/images/` 目录，读取文件元数据。

### Phase 3: 功能模块去重

**首页 (Dashboard) 简化：**
- 保留：统计数字（累计下载数、转录音频时长、生成笔记数、图片数）
- 移除：「最近下载」「最近转录」具体列表
- 新增：快捷操作卡片（「搜索播客」「上传音频」「生成图片」）点击跳转对应页面

**Search 页面简化：**
- 移除 DownloadManager 侧边栏
- 下载完成后显示 Toast 提示「已添加到文件库」
- 用户前往「文件库」查看和管理下载

**内容创作页面（Content + Images 合并）：**
- 顶部标签切换：「AI 笔记生成」/「图片生成」
- 「AI 笔记生成」：保留现有 Content 页面功能
- 「图片生成」：保留现有 Images 页面功能

---

## 实施步骤

### Task 1: 重构 Sidebar 导航

**Files:**
- Modify: `web-dashboard/src/components/Sidebar.tsx`

- [ ] **Step 1: 更新导航项**

将 `navItems` 从 8 项改为 5 项：

```typescript
const navItems = [
  { icon: LayoutDashboard, label: "概览", href: "/dashboard" },
  { icon: Search, label: "播客搜索", href: "/dashboard/search" },
  { icon: FolderOpen, label: "文件库", href: "/dashboard/library" },
  { icon: Sparkles, label: "内容创作", href: "/dashboard/create" },
  { icon: Settings, label: "系统设置", href: "/dashboard/settings" },
];
```

### Task 2: 创建文件库页面

**Files:**
- Create: `web-dashboard/src/app/dashboard/library/page.tsx`
- Create: `backend/routers/library.py`
- Modify: `backend/main.py` (注册路由)

- [ ] **Step 1: 创建后端 `library.py` 路由**

扫描 data 目录，返回文件列表：

```python
@router.get("/files")
async def get_library_files(
    type: str = "all",
    search: str = "",
    sort: str = "time_desc",
    time_range: str = "all"
):
    # 扫描 data/audio/, data/transcripts/, data/images/
    # 根据参数筛选、排序、搜索
    # 返回统一格式的文件列表
```

- [ ] **Step 2: 创建前端文件库页面**

包含：分类标签页、搜索栏、筛选器、文件列表、空状态、操作按钮（打开位置、查看、删除）。

### Task 3: 合并内容创作页面

**Files:**
- Create: `web-dashboard/src/app/dashboard/create/page.tsx`
- Delete: `web-dashboard/src/app/dashboard/content/page.tsx`
- Delete: `web-dashboard/src/app/dashboard/images/page.tsx`

- [ ] **Step 1: 创建合并后的 Create 页面**

顶部 Tab 切换：「AI 笔记生成」/「图片生成」
- 笔记生成 Tab：复用 Content 页面代码
- 图片生成 Tab：复用 Images 页面代码

### Task 4: 简化首页 Dashboard

**Files:**
- Modify: `web-dashboard/src/app/dashboard/page.tsx`

- [ ] **Step 1: 移除最近下载/转录列表**
- [ ] **Step 2: 添加快捷操作卡片**

四个卡片：搜索播客、上传音频、生成笔记、生成图片，点击跳转对应页面。

### Task 5: 简化 Search 页面

**Files:**
- Modify: `web-dashboard/src/app/dashboard/search/page.tsx`

- [ ] **Step 1: 移除 DownloadManager 侧边栏**
- [ ] **Step 2: 下载完成后显示 Toast 提示**

### Task 6: 清理废弃页面

**Files:**
- Delete: `web-dashboard/src/app/dashboard/downloads/page.tsx`
- Delete: `web-dashboard/src/app/dashboard/transcripts/page.tsx`
- Delete: `web-dashboard/src/app/dashboard/publish/page.tsx`

### Task 7: 构建与验证

- [ ] **Step 1: Frontend build**
- [ ] **Step 2: Backend syntax check**
- [ ] **Step 3: 验证导航跳转正常**
- [ ] **Step 4: 验证文件库 API 返回正确数据**

---

## 预期效果与衡量指标

| 指标 | 当前 | 优化后 | 衡量方式 |
|------|------|--------|----------|
| 导航项数量 | 8 | 5 | 直接计数 |
| 文件管理入口 | 0 | 1（统一） | 功能验收 |
| 功能冗余页面 | 3处下载任务展示 | 1处 | 代码审查 |
| 未实现功能占位 | 1（Publish） | 0 | 直接计数 |
| 页面刷新数据保留 | 否（前端状态） | 是（文件扫描） | 功能测试 |
| 用户核心路径步骤 | 4步跨4页 | 4步跨3页 | 用户流程分析 |

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `web-dashboard/src/components/Sidebar.tsx` | 修改 | 导航改为5项 |
| `web-dashboard/src/app/dashboard/page.tsx` | 修改 | 简化首页，添加快捷卡片 |
| `web-dashboard/src/app/dashboard/search/page.tsx` | 修改 | 移除 DownloadManager |
| `web-dashboard/src/app/dashboard/library/page.tsx` | 新建 | 文件库主页面 |
| `web-dashboard/src/app/dashboard/create/page.tsx` | 新建 | 内容创作合并页 |
| `backend/routers/library.py` | 新建 | 文件扫描 API |
| `backend/main.py` | 修改 | 注册 library 路由 |
| `web-dashboard/src/app/dashboard/downloads/page.tsx` | 删除 | 功能合并入文件库 |
| `web-dashboard/src/app/dashboard/transcripts/page.tsx` | 删除 | 功能合并入文件库 |
| `web-dashboard/src/app/dashboard/content/page.tsx` | 删除 | 功能合并入创作页 |
| `web-dashboard/src/app/dashboard/images/page.tsx` | 删除 | 功能合并入创作页 |
| `web-dashboard/src/app/dashboard/publish/page.tsx` | 删除 | 未实现功能 |
