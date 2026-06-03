# Dashboard 功能不可用问题定位报告

> **日期**: 2026-05-27
> **排查范围**: 前端 Dashboard (Next.js) + 后端 Python 服务
> **状态**: 完成

---

## 执行摘要

**根本原因**: Dashboard 所有功能模块**均未实现真实后端 API 调用**，全部使用前端 Mock 数据。项目架构为"前端静态展示 + Python CLI 工具"，而非"前后端分离的 Web 应用"。

**影响范围**: 100% 的 Dashboard 功能处于不可用状态（搜索、下载、转录、内容提炼、图片生成、发布、设置）。

---

## 一、项目架构分析

### 1.1 当前架构

```
┌─────────────────────────────────────────────────────────────┐
│                      项目架构现状                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐         ┌──────────────────────────┐    │
│   │  Next.js 16  │         │    Python CLI 工具        │    │
│   │  (前端展示)   │  ←──×──→│   (独立命令行程序)        │    │
│   │              │  无连接  │                          │    │
│   │  - Mock 数据 │         │  - 播客搜索               │    │
│   │  - 纯前端交互 │         │  - 内容处理               │    │
│   │  - 无 API 调用│         │  - 图片生成               │    │
│   └──────────────┘         └──────────────────────────┘    │
│                                                             │
│   关键问题: 两个系统完全独立，没有任何数据交互通道              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 应有的架构

```
┌─────────────────────────────────────────────────────────────┐
│                      目标架构                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐         ┌──────────────────────────┐    │
│   │  Next.js 16  │◄───────►│   FastAPI / Flask         │    │
│   │  (前端应用)   │  HTTP   │   (后端 API 服务)         │    │
│   │              │         │                          │    │
│   │  - 真实 API  │         │  - 播客搜索 API           │    │
│   │  - 状态管理  │         │  - 内容处理 API           │    │
│   │  - 用户认证  │         │  - 文件下载 API           │    │
│   └──────────────┘         └──────────────────────────┘    │
│                                    │                        │
│                                    ▼                        │
│                           ┌──────────────┐                 │
│                           │  Python Core  │                 │
│                           │  (业务逻辑)   │                 │
│                           └──────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、功能模块详细排查

### 2.1 播客搜索 (Search)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/search/page.tsx` |
| 后端 API | 不存在 | Python `podcast_search.py` 仅为 CLI 工具 |
| 数据流 | Mock | `mockResults` 硬编码数组，无 `fetch` 调用 |
| 搜索逻辑 | 模拟 | `setTimeout(1500)` 后返回固定数据 |

**代码证据**:
```typescript
// page.tsx:50-57
const handleSearch = async () => {
  setIsSearching(true);
  await new Promise((resolve) => setTimeout(resolve, 1500));
  setResults(mockResults);  // ← 硬编码数据
  setIsSearching(false);
};
```

---

### 2.2 下载管理 (Downloads)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/downloads/page.tsx` |
| 后端 API | 不存在 | 无下载队列管理服务 |
| 数据流 | Mock | `tasks` 硬编码数组 |
| 下载功能 | 不可用 | 仅展示静态列表，无真实下载逻辑 |

---

### 2.3 转录文本 (Transcripts)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/transcripts/page.tsx` |
| 后端 API | 不存在 | Python 无转录服务暴露 |
| 数据流 | Mock | `transcripts` 硬编码数组 |
| 转录功能 | 不可用 | 无音频上传/处理逻辑 |

---

### 2.4 内容提炼 (Content)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/content/page.tsx` |
| 后端 API | 不存在 | Python `content_processor.py` 仅为模块 |
| 数据流 | Mock | `mockNote` 硬编码对象 |
| AI 处理 | 不可用 | `setTimeout(2000)` 后返回固定笔记 |

**代码证据**:
```typescript
// page.tsx:45-51
const handleProcess = async () => {
  setIsProcessing(true);
  await new Promise((resolve) => setTimeout(resolve, 2000));
  setNote(mockNote);  // ← 固定内容
  setIsProcessing(false);
};
```

---

### 2.5 图片生成 (Images)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/images/page.tsx` |
| 后端 API | 不存在 | Python `image_generator.py` 未暴露为服务 |
| 数据流 | Mock | `images` 硬编码数组（渐变占位符） |
| 生成功能 | 不可用 | 无图片生成调用 |

---

### 2.6 发布管理 (Publish)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/publish/page.tsx` |
| 后端 API | 不存在 | 无发布服务 |
| 数据流 | Mock | `tasks` 硬编码数组 |
| 发布功能 | 不可用 | 无平台 API 对接 |

---

### 2.7 系统设置 (Settings)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `dashboard/settings/page.tsx` |
| 后端 API | 不存在 | 无配置持久化服务 |
| 数据流 | 本地状态 | `useState` 管理，页面刷新丢失 |
| 保存功能 | 不可用 | `handleSave` 仅设置 `saved=true`，无 API 调用 |

**代码证据**:
```typescript
// settings/page.tsx:124-128
const handleSave = () => {
  // TODO: API call to save settings  // ← 明确标注未实现
  setSaved(true);
  setTimeout(() => setSaved(false), 3000);
};
```

---

### 2.8 文档校对 (Proofread)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `DocumentPreview.tsx` |
| 后端 API | 部分存在 | `app/api/proofread/route.ts` |
| 数据流 | Mock | API 返回固定 `mockIssues` |
| LLM 调用 | 不可用 | 注释明确标注 `"Mock response for now"` |

**代码证据**:
```typescript
// api/proofread/route.ts:14-24
// Mock response for now - will be replaced with actual LLM call
const mockIssues = [
  { id: '1', line: 12, original: '快速的', suggestion: '快速地', type: 'grammar', ... }
];
```

---

### 2.9 文档下载 (Download)

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 前端实现 | 存在 | `DownloadModal.tsx` + `fileDownloader.ts` |
| 后端 API | 存在 | `app/api/download/route.ts` |
| 数据流 | 可用 | 客户端生成 Blob 下载 |
| 实际功能 | 部分可用 | 仅支持客户端打包下载，无后端文件存储 |

---

## 三、API 路由清单

| 路由 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/proofread` | POST | Mock | 返回固定数据 |
| `/api/download` | POST | 可用 | 文件下载服务 |
| `/api/search` | - | 不存在 | 未实现 |
| `/api/transcribe` | - | 不存在 | 未实现 |
| `/api/process` | - | 不存在 | 未实现 |
| `/api/generate-image` | - | 不存在 | 未实现 |
| `/api/publish` | - | 不存在 | 未实现 |
| `/api/settings` | - | 不存在 | 未实现 |
| `/api/auth/login` | - | 不存在 | 未实现 |
| `/api/auth/register` | - | 不存在 | 未实现 |

---

## 四、后端服务状态

### 4.1 Python 模块清单

| 模块 | 路径 | 类型 | 暴露为 API | 说明 |
|------|------|------|-----------|------|
| `podcast_search.py` | `services/` | CLI 工具 | 否 | PodcastIndex/iTunes 搜索 |
| `content_processor.py` | `core/` | 模块 | 否 | LLM 内容提炼 |
| `image_generator.py` | `core/` | 模块 | 否 | 图片生成 |
| `transcription.py` | `core/` | 模块 | 否 | 语音转录 |
| `config/settings.py` | `config/` | 配置 | 否 | 环境变量配置 |

### 4.2 关键发现

- **无 Web 框架**: Python 端未使用 FastAPI/Flask/Django 等任何 Web 框架
- **无 HTTP 服务**: 未启动任何 HTTP 服务器监听端口
- **CLI 入口**: `main.py` 为命令行入口，非 Web 服务入口
- **模块独立**: Python 模块仅能被导入使用，无法通过 HTTP 访问

---

## 五、问题根因分析

### 5.1 直接原因

1. **前端无 API 调用**: 所有 Dashboard 页面使用 `setTimeout` + Mock 数据模拟异步操作
2. **后端无 API 服务**: Python 代码仅为 CLI 工具和模块，未暴露 HTTP 接口
3. **前后端无连接**: 两个系统完全独立，没有任何通信机制

### 5.2 深层原因

1. **架构设计缺失**: 项目初始设计为 CLI 工具，Dashboard 是后期追加的纯前端展示
2. **开发阶段错位**: 前端进入"视觉实现"阶段时，后端仍停留在"模块开发"阶段
3. **接口契约未定义**: 无 API 文档、无接口规范、无数据格式约定

---

## 六、修复路径建议

### 方案 A: 最小可行产品 (推荐)

**目标**: 快速打通前后端，让核心功能可用

**步骤**:
1. 使用 FastAPI 创建后端服务 (`backend/main.py`)
2. 为每个功能模块创建 API 端点:
   - `POST /api/search` → 调用 `podcast_search.py`
   - `POST /api/process` → 调用 `content_processor.py`
   - `POST /api/generate-image` → 调用 `image_generator.py`
3. 前端替换 Mock 数据为 `fetch()` 调用
4. 添加环境变量配置 `NEXT_PUBLIC_API_URL`

**工作量**: 约 3-5 天

### 方案 B: 完整后端服务

**目标**: 建立完整的后端架构

**步骤**:
1. FastAPI + SQLAlchemy + SQLite/PostgreSQL
2. 用户认证系统 (JWT)
3. 任务队列 (Celery + Redis)
4. 文件存储服务
5. 完整的前后端对接

**工作量**: 约 2-3 周

### 方案 C: Serverless 方案

**目标**: 利用现有 Python 模块，最小改动

**步骤**:
1. 使用 `functions` 目录创建 Vercel Serverless Functions
2. 每个功能一个 API 路由
3. 直接调用 Python 模块

**工作量**: 约 1-2 天（但受限于 Vercel Serverless 限制）

---

## 七、验证清单

- [x] 检查前端所有页面是否使用 Mock 数据 → **确认全部使用**
- [x] 检查前端是否有 `fetch`/`axios` 调用 → **仅 `download.ts` 有**
- [x] 检查后端是否有 Web 框架 → **确认无**
- [x] 检查后端是否有 HTTP 服务 → **确认无**
- [x] 检查 API 路由目录 → **仅 2 个路由，1 个为 Mock**
- [x] 检查环境变量配置 → **仅有 `.env`，无 API URL 配置**
- [x] 检查前后端通信机制 → **确认无**

---

## 八、结论

**Dashboard 功能不可用的根本原因是：项目尚未进入"前后端对接"阶段。**

当前状态:
- 前端: 视觉实现完成，使用 Mock 数据展示
- 后端: Python 模块开发完成，但仅为 CLI/库形式
- 缺失: HTTP API 层、前后端通信、数据持久化

**建议优先实施方案 A**，快速建立 FastAPI 后端服务，打通核心功能的数据流，使 Dashboard 从"展示原型"升级为"可用产品"。
