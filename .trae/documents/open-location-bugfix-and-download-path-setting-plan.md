# Bug Fix: "Open Location" File Display + Download Path Setting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the "Open Location" button to reliably open folders and highlight downloaded files across all OSes, and add a user-configurable download location setting with validation.

**Architecture:** Backend stores custom download path in a JSON config file (runtime reloadable). `AudioDownloader` reads this path dynamically. A new FastAPI router handles path validation and persistence. Frontend settings page gets a new "Storage" section with folder picker UI.

**Tech Stack:** FastAPI, Python 3.11+, Pydantic, React/Next.js, Tailwind CSS, Framer Motion, Lucide React

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/routers/download.py` | Modify | Fix `open_download_folder` Windows command escaping; add `GET/POST /api/download/settings` endpoints |
| `backend/routers/settings.py` | Create | New router for download path CRUD + validation |
| `backend/config/download_settings.py` | Create | Pydantic model + JSON file persistence for download path |
| `core/audio_downloader.py` | Modify | Make `download_dir` dynamically read from config at runtime |
| `config/settings.py` | Modify | Add `download_dir_override` field to main Settings |
| `web-dashboard/src/lib/api.ts` | Modify | Add `getDownloadSettings`, `updateDownloadSettings`, `validateDownloadPath` API functions |
| `web-dashboard/src/app/dashboard/settings/page.tsx` | Modify | Add "Storage" section with current path display, folder picker, save/reset buttons |
| `web-dashboard/src/components/DownloadManager.tsx` | Modify | Improve error handling with typed errors instead of string matching |

---

## Task 1: Create Backend Download Settings Persistence

**Files:**
- Create: `backend/config/download_settings.py`
- Modify: `config/settings.py`

- [ ] **Step 1: Create `backend/config/download_settings.py`**

```python
"""Download settings persistence — runtime reloadable path configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from config.settings import settings as app_settings

DEFAULT_CONFIG_PATH = Path("./config/download_config.json")


class DownloadSettingsModel(BaseModel):
    """用户可配置的下载设置."""

    custom_download_dir: str | None = Field(
        default=None,
        description="用户自定义下载目录，None 表示使用默认",
    )

    @field_validator("custom_download_dir")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        """验证路径有效性."""
        if v is None:
            return None
        path = Path(v)
        # 路径必须可写
        if path.exists() and not path.is_dir():
            raise ValueError("路径必须是目录")
        return str(path.resolve())

    def get_effective_download_dir(self) -> Path:
        """获取实际生效的下载目录."""
        if self.custom_download_dir:
            path = Path(self.custom_download_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return app_settings.audio_download_dir


class DownloadSettingsManager:
    """下载设置管理器 — 负责读写 JSON 配置文件."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._settings: DownloadSettingsModel | None = None

    def _ensure_config_dir(self) -> None:
        """确保配置文件目录存在."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> DownloadSettingsModel:
        """从 JSON 文件加载设置."""
        if self._settings is not None:
            return self._settings

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._settings = DownloadSettingsModel(**data)
            except (json.JSONDecodeError, ValueError) as e:
                # 配置文件损坏，使用默认
                self._settings = DownloadSettingsModel()
        else:
            self._settings = DownloadSettingsModel()

        return self._settings

    def save(self, settings: DownloadSettingsModel) -> None:
        """保存设置到 JSON 文件."""
        self._ensure_config_dir()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
        self._settings = settings

    def reset(self) -> DownloadSettingsModel:
        """重置为默认设置."""
        default = DownloadSettingsModel()
        self.save(default)
        return default

    def validate_path(self, path: str) -> dict[str, Any]:
        """验证路径是否可用."""
        result = {
            "valid": False,
            "path": path,
            "error": None,
            "writable": False,
        }
        try:
            p = Path(path)
            # 创建目录（如果不存在）
            p.mkdir(parents=True, exist_ok=True)
            # 测试可写性
            test_file = p / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
                result["writable"] = True
                result["valid"] = True
            except PermissionError:
                result["error"] = "权限不足，无法写入该目录"
            except OSError as e:
                result["error"] = f"目录测试失败: {e}"
        except Exception as e:
            result["error"] = f"路径无效: {e}"
        return result


# 全局管理器实例
download_settings_manager = DownloadSettingsManager()
```

- [ ] **Step 2: Modify `config/settings.py` — add `download_dir_override`**

在 `Settings` 类中，在 `audio_download_dir` property 之前添加：

```python
    download_dir_override: str | None = Field(
        default=None,
        description="用户自定义下载目录覆盖",
    )
```

并修改 `audio_download_dir` property：

```python
    @property
    def audio_download_dir(self) -> Path:
        """音频下载目录."""
        # 优先使用覆盖路径
        if self.download_dir_override:
            path = Path(self.download_dir_override)
        else:
            path = self.data_dir / "audio"
        path.mkdir(parents=True, exist_ok=True)
        return path
```

---

## Task 2: Fix "Open Location" Bug in Backend

**Files:**
- Modify: `backend/routers/download.py`

- [ ] **Step 1: Fix Windows `explorer` command escaping**

当前代码：
```python
cmd = ['explorer', f'/select,"{str(file_path)}"']
subprocess.Popen(cmd, shell=True)
```

问题：`shell=True` 时传入列表会导致命令解析错误。应改为字符串命令：

```python
if system == "Windows":
    # Windows: explorer /select,"path" — 必须作为单个字符串传递
    cmd = f'explorer /select,"{str(file_path)}"'
    subprocess.Popen(cmd, shell=True)
```

- [ ] **Step 2: Add typed error response model for better frontend handling**

在 `OpenFolderResponse` 中添加 `error_code` 字段：

```python
class OpenFolderResponse(BaseModel):
    """Open folder response model."""

    success: bool
    message: str
    file_path: str | None = None
    error_code: str | None = None  # 'not_found' | 'not_completed' | 'file_missing' | 'permission_denied' | 'unsupported_os' | 'open_failed'
```

修改 `open_download_folder` 函数，在每次 raise HTTPException 前设置对应的 `error_code`。

---

## Task 3: Create Settings Router for Download Path

**Files:**
- Create: `backend/routers/settings.py`

- [ ] **Step 1: Create the settings router**

```python
"""Settings router for user-configurable application settings."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config.download_settings import (
    DownloadSettingsModel,
    download_settings_manager,
)
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/settings")


class DownloadPathRequest(BaseModel):
    """Update download path request."""

    path: str


class DownloadPathResponse(BaseModel):
    """Download path response."""

    current_path: str
    is_custom: bool
    default_path: str


class PathValidationResponse(BaseModel):
    """Path validation response."""

    valid: bool
    path: str
    writable: bool
    error: str | None = None


@router.get("/download-path", response_model=DownloadPathResponse)
async def get_download_path():
    """获取当前下载路径设置."""
    settings = download_settings_manager.load()
    effective = settings.get_effective_download_dir()
    default = download_settings_manager.load().model_dump().get("custom_download_dir") is None

    return DownloadPathResponse(
        current_path=str(effective),
        is_custom=settings.custom_download_dir is not None,
        default_path=str(effective if not settings.custom_download_dir else ""),
    )


@router.post("/download-path", response_model=DownloadPathResponse)
async def set_download_path(request: DownloadPathRequest):
    """设置自定义下载路径."""
    # 先验证
    validation = download_settings_manager.validate_path(request.path)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])

    settings = download_settings_manager.load()
    settings.custom_download_dir = request.path
    download_settings_manager.save(settings)

    effective = settings.get_effective_download_dir()
    return DownloadPathResponse(
        current_path=str(effective),
        is_custom=True,
        default_path="",
    )


@router.post("/download-path/reset", response_model=DownloadPathResponse)
async def reset_download_path():
    """重置为默认下载路径."""
    settings = download_settings_manager.reset()
    effective = settings.get_effective_download_dir()
    return DownloadPathResponse(
        current_path=str(effective),
        is_custom=False,
        default_path=str(effective),
    )


@router.post("/download-path/validate", response_model=PathValidationResponse)
async def validate_download_path(request: DownloadPathRequest):
    """验证下载路径是否可用."""
    result = download_settings_manager.validate_path(request.path)
    return PathValidationResponse(
        valid=result["valid"],
        path=result["path"],
        writable=result["writable"],
        error=result["error"],
    )
```

- [ ] **Step 2: Register the new router in `backend/main.py`**

Find where other routers are registered and add:
```python
from backend.routers import settings as settings_router

app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
```

---

## Task 4: Make AudioDownloader Use Dynamic Path

**Files:**
- Modify: `core/audio_downloader.py`

- [ ] **Step 1: Import and use dynamic settings**

```python
from backend.config.download_settings import download_settings_manager
```

Modify `__init__` to read path dynamically:

```python
def __init__(self, download_dir: Path | None = None) -> None:
    """初始化下载器.

    Args:
        download_dir: 音频下载目录，默认使用配置中的目录
    """
    if download_dir:
        self.download_dir = download_dir
    else:
        # 动态读取用户配置
        ds = download_settings_manager.load()
        self.download_dir = ds.get_effective_download_dir()
    self.timeout = settings.request_timeout
```

---

## Task 5: Frontend API Client — Add Settings Functions

**Files:**
- Modify: `web-dashboard/src/lib/api.ts`

- [ ] **Step 1: Add interfaces and API functions**

在文件末尾（Image Generation 之后）添加：

```typescript
// Download Settings
export interface DownloadPathResponse {
  current_path: string;
  is_custom: boolean;
  default_path: string;
}

export interface PathValidationResponse {
  valid: boolean;
  path: string;
  writable: boolean;
  error?: string;
}

export async function getDownloadSettings(): Promise<DownloadPathResponse> {
  return fetchApi<DownloadPathResponse>("/api/settings/download-path");
}

export async function updateDownloadSettings(path: string): Promise<DownloadPathResponse> {
  return fetchApi<DownloadPathResponse>("/api/settings/download-path", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function resetDownloadSettings(): Promise<DownloadPathResponse> {
  return fetchApi<DownloadPathResponse>("/api/settings/download-path/reset", {
    method: "POST",
  });
}

export async function validateDownloadPath(path: string): Promise<PathValidationResponse> {
  return fetchApi<PathValidationResponse>("/api/settings/download-path/validate", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}
```

---

## Task 6: Frontend Settings Page — Add Storage Section

**Files:**
- Modify: `web-dashboard/src/app/dashboard/settings/page.tsx`

- [ ] **Step 1: Add imports**

```typescript
import { FolderOpen, RotateCcw, HardDrive } from "lucide-react";
import {
  getDownloadSettings,
  updateDownloadSettings,
  resetDownloadSettings,
  validateDownloadPath,
} from "@/lib/api";
```

- [ ] **Step 2: Add state for download path**

```typescript
const [downloadPath, setDownloadPath] = useState("");
const [isCustomPath, setIsCustomPath] = useState(false);
const [pathError, setPathError] = useState("");
const [pathLoading, setPathLoading] = useState(false);
```

- [ ] **Step 3: Load current path on mount**

```typescript
useEffect(() => {
  getDownloadSettings()
    .then((res) => {
      setDownloadPath(res.current_path);
      setIsCustomPath(res.is_custom);
    })
    .catch(() => {
      // silently fail, show empty
    });
}, []);
```

- [ ] **Step 4: Add "Storage" section to settingsData or as a separate card**

在 settingsData 数组后添加一个新的独立 section（不放在 settingsData 中，因为需要更复杂的交互）：

在 JSX 中，在 `{settingsData.map(...)}` 之后、Save Button 之前插入：

```tsx
{/* Storage Section */}
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.4, duration: 0.5 }}
  className="bg-[#0c0c0e]/70 border border-gray-900 rounded-3xl p-6 backdrop-blur-md mt-6"
>
  <div className="flex items-center gap-3 mb-4">
    <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
      <HardDrive className="w-4 h-4 text-gray-400" />
    </div>
    <div>
      <h3 className="text-sm font-semibold text-white">存储设置</h3>
      <p className="text-xs text-gray-600">配置音频下载保存位置</p>
    </div>
  </div>

  <div className="space-y-4">
    {/* Current path display */}
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-gray-500 mb-1.5 font-medium">
        当前下载目录
      </label>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={downloadPath}
          readOnly
          className="flex-1 bg-[#141416] border border-gray-900 rounded-xl px-4 py-3 text-sm text-gray-400 cursor-not-allowed"
        />
        {isCustomPath && (
          <button
            onClick={async () => {
              setPathLoading(true);
              try {
                const res = await resetDownloadSettings();
                setDownloadPath(res.current_path);
                setIsCustomPath(false);
                setPathError("");
              } catch (e: any) {
                setPathError(e.message || "重置失败");
              } finally {
                setPathLoading(false);
              }
            }}
            disabled={pathLoading}
            className="px-4 py-3 bg-white/5 border border-gray-800 rounded-xl text-xs text-gray-400 hover:text-white hover:bg-white/10 transition disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        )}
      </div>
      {isCustomPath && (
        <p className="text-[10px] text-emerald-400 mt-1">已使用自定义路径</p>
      )}
    </div>

    {/* New path input */}
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-gray-500 mb-1.5 font-medium">
        自定义下载目录
      </label>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={customPath}
          onChange={(e) => {
            setCustomPath(e.target.value);
            setPathError("");
          }}
          placeholder="输入完整路径，如 D:\\Podcasts\\Downloads"
          className="flex-1 bg-[#141416] border border-gray-900 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-700 transition"
        />
        <button
          onClick={async () => {
            if (!customPath.trim()) return;
            setPathLoading(true);
            try {
              // Validate first
              const validation = await validateDownloadPath(customPath.trim());
              if (!validation.valid) {
                setPathError(validation.error || "路径无效");
                setPathLoading(false);
                return;
              }
              // Save
              const res = await updateDownloadSettings(customPath.trim());
              setDownloadPath(res.current_path);
              setIsCustomPath(true);
              setCustomPath("");
              setPathError("");
            } catch (e: any) {
              setPathError(e.message || "保存失败");
            } finally {
              setPathLoading(false);
            }
          }}
          disabled={pathLoading || !customPath.trim()}
          className="px-4 py-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 hover:bg-emerald-500/20 transition disabled:opacity-50"
        >
          {pathLoading ? "处理中..." : "保存"}
        </button>
      </div>
      {pathError && (
        <p className="text-[10px] text-red-400 mt-1">{pathError}</p>
      )}
    </div>
  </div>
</motion.div>
```

注意：需要添加 `const [customPath, setCustomPath] = useState("");` 到 state 中。

---

## Task 7: Improve DownloadManager Error Handling

**Files:**
- Modify: `web-dashboard/src/components/DownloadManager.tsx`

- [ ] **Step 1: Replace string matching with typed error handling**

修改 `openDownloadFolder` 调用处的错误处理：

```typescript
import { ApiError } from "@/lib/api";

// ...

try {
  await openDownloadFolder(task.taskId);
} catch (err: any) {
  const status = err?.status;
  const msg = err?.message || "";

  if (status === 404) {
    if (msg.includes("任务不存在")) {
      alert("下载任务不存在");
    } else {
      alert("文件已被移动或删除，请重新下载");
    }
  } else if (status === 400) {
    alert("文件尚未下载完成");
  } else if (status === 403) {
    alert("权限不足，请检查文件夹访问权限");
  } else if (status === 500) {
    alert(`打开文件夹失败，请手动前往: ${task.result?.file_path || "未知路径"}`);
  } else {
    alert(`打开文件夹失败: ${msg}`);
  }
}
```

---

## Task 8: Build and Test

- [ ] **Step 1: Frontend build**

Run: `cd web-dashboard && npm run build`
Expected: No TypeScript or build errors

- [ ] **Step 2: Backend syntax check**

Run: `python -m py_compile backend/routers/download.py`
Run: `python -m py_compile backend/routers/settings.py`
Run: `python -m py_compile backend/config/download_settings.py`
Run: `python -m py_compile core/audio_downloader.py`
Expected: All pass silently

- [ ] **Step 3: Integration test — start backend and test endpoints**

1. Start backend: `uvicorn backend.main:app --reload`
2. Test GET `/api/settings/download-path` → should return default path
3. Test POST `/api/settings/download-path/validate` with `"path": "C:\\test"` → should return valid/writable
4. Test POST `/api/settings/download-path` with valid path → should save
5. Test POST `/api/settings/download-path/reset` → should reset to default

- [ ] **Step 4: Test "Open Location" button**

1. Download a podcast episode
2. Click "打开位置" → folder should open with file highlighted (Windows) or folder opened (macOS/Linux)
3. Move/delete the file
4. Click "打开位置" again → should show "文件已被移动或删除" alert

---

## Verification Checklist

- [ ] `explorer /select,"path"` works on Windows with spaces in path
- [ ] Custom download path persists across backend restarts
- [ ] Downloaded files go to custom path when set
- [ ] Reset button restores default path
- [ ] Invalid path shows clear error message
- [ ] Frontend build passes
- [ ] Backend starts without import errors
