# 修复转录页面标签统计数字不一致问题

## 问题分析

### 现象
点击不同功能模块标签时，统计数字错误变化：
- **全部**标签应始终显示所有文件总数（13）
- **音频**标签应始终显示音频文件数（7）
- **转录**标签应始终显示转录文件数（6）
- **图片**标签应始终显示图片文件数（0）

### 实际表现（Bug）
| 点击标签 | 全部 | 音频 | 转录 | 图片 |
|---------|------|------|------|------|
| 全部 | 13 | 7 | 6 | 0 |
| 音频 | **7** | **7** | **0** | **0** |
| 转录 | **6** | **0** | **6** | **0** |

### 根本原因

**后端 `backend/routers/library.py:139-143`**：
```python
if type == "all":
    for ft, dir_path in type_dirs.items():
        all_files.extend(_scan_directory(dir_path, ft, search, time_range))
elif type in type_dirs:
    all_files.extend(_scan_directory(type_dirs[type], type, search, time_range))
```

当 `type != "all"` 时（如点击"音频"标签），后端只扫描该类型的目录，导致：
- `all_files` 只包含该类型的文件
- `type_counts` 基于 `all_files` 计算，其他类型变为 0
- 返回给前端的 `type_counts` 是错误的

**前端 `web-dashboard/src/app/dashboard/library/page.tsx:376`**：
```tsx
{tab.key === "all" ? files.length : typeCounts[tab.key] || 0}
```

前端显示逻辑：
- "全部"标签显示 `files.length`（当前筛选后的文件数）
- 其他标签显示 `typeCounts[tab.key]`

当点击"音频"标签时：
- `files` = 7 个音频文件
- `typeCounts` = `{audio: 7, transcript: 0, image: 0}`（后端错误返回）
- "全部"显示 `files.length` = 7（错误！应为 13）

---

## 修复方案

### 方案 A：后端始终返回完整统计（推荐）

**修改 `backend/routers/library.py`**：
- 无论 `type` 参数是什么，始终扫描所有目录获取完整文件列表
- 用完整列表计算 `type_counts`
- 再根据 `type` 参数筛选返回的 `files`

**优点**：
- 统计数字始终准确
- 前端逻辑无需修改
- 符合用户预期（标签统计应反映全局状态）

### 方案 B：前端独立获取统计

**修改前端**：
- 额外调用一次 `type=all` 获取完整统计
- 标签数字使用独立统计，文件列表使用筛选后的

**缺点**：
- 额外 API 调用
- 增加复杂度

---

## 实施计划

### 步骤 1：修复后端统计逻辑
**文件**：`backend/routers/library.py`
**修改**：
1. 始终扫描所有目录获取 `all_files_for_counts`
2. 基于完整列表计算 `type_counts`
3. 根据 `type` 参数筛选返回的 `files`

### 步骤 2：修复前端"全部"标签显示
**文件**：`web-dashboard/src/app/dashboard/library/page.tsx`
**修改**：
1. "全部"标签应显示 `typeCounts.audio + typeCounts.transcript + typeCounts.image`
2. 或添加独立的 `total` 字段

### 步骤 3：添加测试用例
**文件**：`tests/test_library_counts.py`
**测试**：
1. 点击不同标签时 type_counts 保持一致
2. 全部标签显示正确总数
3. 各类型标签显示正确数量

### 步骤 4：验证修复
- 运行测试
- 构建前端
- 手动验证各标签统计

---

## 预期结果

修复后，无论点击哪个标签，统计数字始终一致：
| 点击标签 | 全部 | 音频 | 转录 | 图片 |
|---------|------|------|------|------|
| 全部 | 13 | 7 | 6 | 0 |
| 音频 | 13 | 7 | 6 | 0 |
| 转录 | 13 | 7 | 6 | 0 |
| 图片 | 13 | 7 | 6 | 0 |
