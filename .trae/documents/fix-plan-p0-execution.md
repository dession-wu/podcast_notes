# P0 修复计划执行文档

> **原始计划**: `fix-plan-p0.md`（已批准）
> **状态**: 执行中
> **目标**: 修复产品检查报告中 P0 级别问题

---

## 已批准任务清单（8个任务）

### Task 1: 移除前端硬编码 API Key
- **文件**: `web-dashboard/src/app/dashboard/settings/page.tsx`
- **修改**: 删除 `podcastindex_key` 默认值，改为空字符串
- **状态**: 待执行

### Task 2: XSS 防护 — DocumentPreview 组件
- **文件**: `web-dashboard/src/components/DocumentPreview.tsx`
- **修改**: 引入 DOMPurify 清理 HTML
- **状态**: 待执行

### Task 3: 添加基础路由守卫
- **文件**: 新建 `AuthGuard.tsx`，修改 `layout.tsx` 和 `page.tsx`
- **修改**: 模拟认证状态检查
- **状态**: 待执行

### Task 4: 添加 "开发中" 提示
- **文件**: 所有 `dashboard/*/page.tsx`
- **修改**: 顶部添加黄色提示条
- **状态**: 待执行

### Task 5: 修复 Sidebar 动画类型错误
- **文件**: `web-dashboard/src/components/Sidebar.tsx`
- **修改**: `x: -100 + "%"` → `x: "-100%"`
- **状态**: 待执行

### Task 6: 修复搜索页 Podcast 图标
- **文件**: `web-dashboard/src/app/dashboard/search/page.tsx`
- **修改**: 确认/替换 Podcast 图标
- **状态**: 待执行

### Task 7: 添加 try-catch 到 clipboard 操作
- **文件**: `web-dashboard/src/app/dashboard/content/page.tsx`
- **修改**: 添加错误处理和 toast 提示
- **状态**: 待执行

### Task 8: 构建验证
- **命令**: `npm run build`
- **验证**: 无错误，无密钥泄露
- **状态**: 待执行

---

## 执行顺序

1. Task 1 → Task 5 → Task 6（独立修改，可并行）
2. Task 2（依赖 DOMPurify 安装）
3. Task 3（新建组件，修改布局）
4. Task 4（批量修改所有页面）
5. Task 7（独立修改）
6. Task 8（最终验证）

---

## 风险预防

- 所有修改不引入新依赖（除 DOMPurify）
- 保持现有功能不变
- 仅修复安全问题，不重构架构
- 每次修改后检查 TypeScript 类型
