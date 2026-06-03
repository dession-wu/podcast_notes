# "查看下载位置"功能完善实施计划

## 1. 问题分析

### 1.1 当前问题
- **前端**：`DownloadManager.tsx` 中"打开位置"按钮仅调用 `alert()` 显示文件路径，无法真正打开文件夹
- **后端**：缺少打开文件夹/高亮文件的 API 接口
- **跨平台**：未处理 Windows/macOS/Linux 不同系统打开文件夹的差异

### 1.2 需求目标
- 点击"查看下载位置"后，能在3秒内打开对应文件夹并高亮显示已下载文件
- 提供清晰的错误提示和解决方案建议
- 确保功能在所有支持的操作系统版本中稳定运行

## 2. 技术方案

### 2.1 后端方案
新增 `POST /api/download/open-folder/{task_id}` 接口：
1. 根据 `task_id` 从 `jobs` 字典获取下载结果中的 `file_path`
2. 验证文件是否存在
3. 根据操作系统类型选择对应命令打开文件夹并高亮文件：
   - **Windows**: `explorer /select,"{file_path}"`
   - **macOS**: `open -R "{file_path}"`
   - **Linux**: `xdg-open "{folder_path}"`（Linux 无法直接高亮文件，打开所在文件夹）
4. 使用 `subprocess` 非阻塞执行系统命令
5. 返回操作结果或错误信息

### 2.2 前端方案
修改 `DownloadManager.tsx` 中"打开位置"按钮：
1. 调用新增的后端 API `POST /api/download/open-folder/{task_id}`
2. 显示加载状态
3. 根据返回结果显示成功提示或错误信息（使用 Toast 通知）
4. 在 `api.ts` 中添加 `openDownloadFolder(taskId)` 函数

## 3. 实施步骤

### Step 1: 后端实现 - 添加打开文件夹 API
**文件**: `backend/routers/download.py`

- 导入 `subprocess`、`platform` 模块
- 添加 `OpenFolderResponse` Pydantic 模型
- 添加 `POST /api/download/open-folder/{task_id}` 路由处理函数：
  - 检查 task_id 是否存在
  - 检查任务是否已完成且有结果
  - 检查文件路径是否存在
  - 根据 `platform.system()` 判断操作系统：
    - `"Windows"` → `explorer /select,"{path}"`
    - `"Darwin"` → `open -R "{path}"`
    - `"Linux"` → `xdg-open "{folder}"`
  - 使用 `subprocess.Popen` 非阻塞执行
  - 捕获异常并返回友好错误信息

### Step 2: 前端 API 客户端 - 添加打开文件夹函数
**文件**: `web-dashboard/src/lib/api.ts`

- 添加 `OpenFolderResponse` 接口
- 添加 `openDownloadFolder(taskId: string)` 异步函数
- 发送 POST 请求到 `/api/download/open-folder/{taskId}`

### Step 3: 前端组件 - 修改"打开位置"按钮行为
**文件**: `web-dashboard/src/components/DownloadManager.tsx`

- 导入 `openDownloadFolder` API 函数
- 修改"打开位置"按钮的 `onClick` 处理逻辑：
  - 调用 `openDownloadFolder(task.taskId)`
  - 使用 try-catch 处理错误
  - 显示操作结果（成功/失败提示）
- 添加 `onOpenLocation` 到 props 接口（或直接在组件内调用）

### Step 4: 构建与验证
- 运行 `npm run build`（前端）
- 运行后端服务
- 测试"打开位置"功能

## 4. 错误处理策略

| 场景 | 处理方式 |
|------|----------|
| 任务不存在 | 返回 404，提示"下载任务不存在" |
| 任务未完成 | 返回 400，提示"文件尚未下载完成" |
| 文件已被移动/删除 | 返回 404，提示"文件已被移动或删除，请重新下载" |
| 权限不足 | 返回 403，提示"权限不足，请检查文件夹访问权限" |
| 系统命令执行失败 | 返回 500，提示"打开文件夹失败，请手动前往: {path}" |
| 未知操作系统 | 返回 500，提示"不支持的操作系统" |

## 5. 验收标准

- [ ] 点击"打开位置"按钮后，能在3秒内打开对应文件夹
- [ ] Windows 系统下能高亮显示已下载文件
- [ ] macOS 系统下能高亮显示已下载文件
- [ ] Linux 系统下能打开所在文件夹
- [ ] 文件不存在时显示明确的错误提示
- [ ] 权限不足时显示明确的错误提示
- [ ] 前端构建无错误
- [ ] 后端运行无异常
