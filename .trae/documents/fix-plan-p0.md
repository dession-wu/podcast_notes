# P0 修复计划 — 产品可用性紧急修复

> **目标**: 修复报告中 P0 级别问题，使产品从"纯演示"变为"可用状态"

---

## 问题总览（P0 级别）

| # | 问题 | 严重程度 | 根因 |
|---|------|---------|------|
| 1 | 前后端完全断联 — 所有页面使用 mock 数据 | 严重 | 无 REST API 服务层 |
| 2 | 缺少 API 中间层 — Python 后端是 CLI 工具 | 严重 | 未引入 FastAPI/Flask |
| 3 | 登录系统纯装饰 — 无认证逻辑 | 中等 | 无用户认证实现 |
| 4 | 前端设置页暴露 API Key | 中等 | 密钥硬编码在前端代码 |
| 5 | XSS 风险 — dangerouslySetInnerHTML | 中等 | 未配置 HTML sanitizer |

---

## 修复策略

### 策略选择：渐进式修复（非重构）

**不选择** "新建 FastAPI + 全量对接" 的原因：
- 工作量大（5-8小时），引入新依赖风险
- 需要设计完整的 API 契约
- 与当前 "计划模式" 约束冲突（用户要求先审计划）

**选择** "最小可行修复" 策略：
- 修复安全漏洞（移除硬编码密钥、XSS 防护）
- 添加基础路由守卫（模拟认证状态）
- 保持 mock 数据但添加 "开发中" 提示
- 为后续真实 API 对接预留接口

---

## 任务清单

### Task 1: 移除前端硬编码 API Key
**文件**: `web-dashboard/src/app/dashboard/settings/page.tsx`
**修改**:
- 删除 `podcastindex_key` 默认值 `"D4AD6GWM6ASG5QDDFGRL"`
- 所有密钥字段默认值为空字符串
- 添加提示："密钥仅保存在本地浏览器存储中"

**验证**: 构建后检查 JS bundle 中无密钥字符串

---

### Task 2: XSS 防护 — DocumentPreview 组件
**文件**: `web-dashboard/src/components/DocumentPreview.tsx`
**修改**:
- 配置 `marked` 使用 `sanitize: true` 或引入 DOMPurify
- 或使用 `marked.parse()` 后通过 DOMPurify 清理

**验证**: 测试 `<script>alert(1)</script>` 不会被注入

---

### Task 3: 添加基础路由守卫
**文件**: 新建 `web-dashboard/src/components/AuthGuard.tsx`
**功能**:
- 检查 `localStorage` 中是否有 `auth_token`
- 无 token 时重定向到 `/` (landing page)
- Landing page 表单提交后设置 `auth_token = "dev"`

**修改**:
- `app/dashboard/layout.tsx` — 包裹 `<AuthGuard>`
- `app/page.tsx` — 表单提交时设置 token

**验证**: 直接访问 `/dashboard` 被重定向到 `/`

---

### Task 4: 添加 "开发中" 提示
**文件**: 所有 `dashboard/*/page.tsx`
**修改**:
- 在每个页面顶部添加黄色提示条：
  "此功能正在开发中，当前展示为演示数据"
- 使用现有 `AlertTriangle` 图标

**验证**: 所有 8 个页面均显示提示

---

### Task 5: 修复 Sidebar 动画类型错误
**文件**: `web-dashboard/src/components/Sidebar.tsx`
**修改**:
- `x: -100 + "%"` → `x: "-100%"`

**验证**: TypeScript 编译通过

---

### Task 6: 修复搜索页 Podcast 图标
**文件**: `web-dashboard/src/app/dashboard/search/page.tsx`
**修改**:
- 确认 `Podcast` 图标从 `lucide-react` 导入是否存在
- 如不存在，替换为 `Radio` 或 `Headphones`

**验证**: 构建无错误

---

### Task 7: 添加 try-catch 到 clipboard 操作
**文件**: `web-dashboard/src/app/dashboard/content/page.tsx`
**修改**:
- `navigator.clipboard.writeText` 添加 try-catch
- 失败时显示 toast 提示

**验证**: 复制功能在 HTTP 环境下不崩溃

---

### Task 8: 构建验证
- `npm run build` 通过
- 检查 JS bundle 中无密钥
- 所有路由可访问

---

## 修复后状态

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 前端硬编码密钥 | ❌ 明文暴露 | ✅ 已移除 |
| XSS 风险 | ❌ 无防护 | ✅ DOMPurify 清理 |
| 无认证 | ❌ 直接访问 | ✅ 路由守卫 + 模拟登录 |
| 用户误解 | ❌ 看似可用 | ✅ "开发中"提示 |
| TS 类型错误 | ❌ 编译风险 | ✅ 修复 |

---

## 不修复的问题（留待后续）

以下问题需要架构级改动，不在 P0 范围内：
- 建立 FastAPI 后端（P1）
- 前端对接真实 API（P1）
- 全局状态管理（P1）
- 集成未使用组件（P1）
- 按钮功能实现（P1）

---

## 预计时间

8 个任务，约 1-1.5 小时
