# Transcription Optimization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix critical transcription failures (English), optimize performance (CPU→GPU/faster-whisper), improve UX (progress, estimates), and ensure 99.9% uptime with <5% error rate.

**Architecture:** Multi-phase rollout: (1) Critical fixes for immediate stability, (2) Performance optimization with faster-whisper integration, (3) UX improvements with real-time progress and accessibility, (4) Comprehensive testing and monitoring.

**Tech Stack:** Python 3.12, FastAPI, faster-whisper, SenseVoice (funasr), Next.js 16, React, TypeScript, Tailwind CSS

---

## Current State Analysis

### Critical Issues Identified

| Issue | Severity | Root Cause | Impact |
|-------|----------|------------|--------|
| English transcription fails | P0 | Whisper not installed; language detection routes English to Whisper | 100% failure rate for English |
| Chinese transcription too slow | P0 | CPU-only execution; no GPU utilization | 3-5 hours for 1-hour audio |
| Progress bar stuck at 20% | P1 | Only 3 progress points (10%, 20%, 100%) | Poor UX, users think it's frozen |
| Inaccurate time estimates | P1 | Formula doesn't account for CPU vs GPU | Shows 1h21m but takes 3-5 hours |
| No error categorization | P2 | Generic error messages | Users can't troubleshoot |

### Performance Baseline

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| 1-hour audio transcription | 3-5 hours | <15 minutes | 12-20x slower |
| English success rate | 0% | 99.9% | Complete failure |
| Progress updates | 3 total | Every 5% | 20x less frequent |
| Estimate accuracy | ~30% | >90% | 3x improvement needed |
| System uptime | Unknown | 99.9% | Need monitoring |

---

## File Structure

### Backend Files
- `core/transcriber.py` - Main transcription engine (Whisper, faster-whisper, SenseVoice)
- `core/language_detector.py` - Language detection for engine routing
- `core/smart_transcriber.py` - Smart routing between engines
- `backend/routers/transcribe.py` - API endpoints for transcription
- `config/settings.py` - Configuration for STT providers
- `utils/metrics.py` - NEW: Performance metrics collection

### Frontend Files
- `src/app/dashboard/library/page.tsx` - Library page with transcription UI
- `src/components/TranscriptionProgress.tsx` - NEW: Real-time progress component
- `src/lib/transcriptionStorage.ts` - Local storage for transcription state
- `src/lib/api.ts` - API client for transcription endpoints

---

## Phase 1: Critical Fixes (P0 - Immediate Stability)

### Task 1: Fix English Transcription Routing

**Files:**
- Modify: `core/language_detector.py:72-79`
- Modify: `core/smart_transcriber.py:68-144`
- Test: `tests/test_language_detector.py`

**Problem:** English audio is routed to Whisper, but Whisper is not installed.

**Solution:** Route all languages to SenseVoice (which supports English) until Whisper is installed.

- [ ] **Step 1: Modify engine mapping**

```python
# In core/language_detector.py, change ENGINE_MAP:
ENGINE_MAP = {
    "zh": "sensevoice",
    "yue": "sensevoice",
    "ja": "sensevoice",
    "ko": "sensevoice",
    "en": "sensevoice",  # Changed from "whisper" to "sensevoice"
}
```

- [ ] **Step 2: Add fallback logic in SmartTranscriber**

```python
# In core/smart_transcriber.py, add fallback:
def _transcribe_with_whisper(self, episode):
    try:
        transcriber = self._get_whisper_transcriber()
        return transcriber.transcribe(episode)
    except Exception as e:
        logger.warning("Whisper failed, falling back to SenseVoice", error=str(e))
        return self._transcribe_with_sensevoice(episode)
```

- [ ] **Step 3: Test language detection**

Run: `pytest tests/test_language_detector.py -v`
Expected: All tests pass, English routes to SenseVoice

- [ ] **Step 4: Commit**

```bash
git add core/language_detector.py core/smart_transcriber.py
git commit -m "fix: route English to SenseVoice as fallback for Whisper"
```

---

### Task 2: Improve Error Handling and Categorization

**Files:**
- Modify: `backend/routers/transcribe.py:47-66`
- Modify: `src/app/dashboard/library/page.tsx:172-216`
- Test: `tests/test_error_handling.py`

**Problem:** Generic error messages like "转录过程中发生错误" don't help users.

**Solution:** Enhance error categorization with specific messages and recovery suggestions.

- [ ] **Step 1: Expand error categories**

```python
# In backend/routers/transcribe.py:
class TranscriptionErrorCategory:
    FILE_NOT_FOUND = "file_not_found"
    INVALID_FORMAT = "invalid_format"
    FILE_TOO_LARGE = "file_too_large"
    MODEL_LOAD_ERROR = "model_load_error"
    MODEL_NOT_INSTALLED = "model_not_installed"  # NEW
    TRANSCRIPTION_ERROR = "transcription_error"
    TIMEOUT = "timeout"  # NEW
    OUT_OF_MEMORY = "out_of_memory"  # NEW
    UNKNOWN_ERROR = "unknown_error"

def _categorize_error(error: Exception) -> tuple[str, str, str]:
    """Categorize error and return (category, message, suggestion)."""
    error_msg = str(error).lower()
    
    if "not installed" in error_msg or "未安装" in error_msg:
        return (
            TranscriptionErrorCategory.MODEL_NOT_INSTALLED,
            "转录模型未安装",
            "请运行: pip install openai-whisper 或联系管理员"
        )
    
    if "out of memory" in error_msg or "cuda" in error_msg:
        return (
            TranscriptionErrorCategory.OUT_OF_MEMORY,
            "内存不足，无法加载模型",
            "尝试转录较短的音频，或联系管理员升级硬件"
        )
    
    if "timeout" in error_msg:
        return (
            TranscriptionErrorCategory.TIMEOUT,
            "转录超时",
            "音频可能太长，尝试分段转录"
        )
    
    # ... existing categories
```

- [ ] **Step 2: Update frontend error display**

```tsx
// In src/app/dashboard/library/page.tsx:
const getErrorMessage = (error: string, category: string | null): string => {
  switch (category) {
    case "model_not_installed":
      return "转录模型未安装，请联系管理员";
    case "out_of_memory":
      return "内存不足，无法完成转录";
    case "timeout":
      return "转录超时，建议分段处理";
    // ... existing cases
  }
};

const getErrorSuggestion = (category: string | null): string => {
  switch (category) {
    case "model_not_installed":
      return "请运行: pip install openai-whisper 或联系管理员配置模型";
    case "out_of_memory":
      return "尝试转录较短的音频片段，或等待系统资源释放";
    case "timeout":
      return "建议将音频分割为 10-15 分钟片段分别转录";
    // ... existing cases
  }
};
```

- [ ] **Step 3: Test error scenarios**

Run: `pytest tests/test_error_handling.py -v`
Expected: All error categories produce correct messages

- [ ] **Step 4: Commit**

```bash
git add backend/routers/transcribe.py src/app/dashboard/library/page.tsx
git commit -m "feat: enhance error categorization with specific messages"
```

---

## Phase 2: Performance Optimization (P0 - Speed)

### Task 3: Integrate faster-whisper

**Files:**
- Modify: `config/settings.py:102-119`
- Modify: `core/transcriber.py:152-198`
- Create: `requirements-faster-whisper.txt`
- Test: `tests/test_faster_whisper.py`

**Problem:** Standard Whisper on CPU is 3-5x slower than real-time.

**Solution:** Integrate faster-whisper which is 3-5x faster with quantization support.

- [ ] **Step 1: Add faster-whisper configuration**

```python
# In config/settings.py:
class STTProvider(str, Enum):
    WHISPER = "whisper"
    FASTER_WHISPER = "faster-whisper"  # Already exists
    SENSEVOICE = "sensevoice"
    ELEVENLABS = "elevenlabs"

# Add faster-whisper specific settings
faster_whisper_model: str = Field(
    default="medium",
    description="faster-whisper model name"
)
faster_whisper_device: Literal["cpu", "cuda", "auto"] = Field(
    default="auto",  # Auto-detect GPU
    description="Device for faster-whisper"
)
faster_whisper_compute_type: Literal["int8", "int8_float16", "float16", "float32"] = Field(
    default="int8",  # Fastest on CPU
    description="Computation type for faster-whisper"
)
```

- [ ] **Step 2: Implement faster-whisper transcription**

```python
# In core/transcriber.py:
def _transcribe_with_faster_whisper(self, audio_path, language):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise TranscriberError(
            "未安装 faster-whisper，请运行: pip install faster-whisper"
        )
    
    if self._faster_whisper_model is None:
        model_name = settings.faster_whisper_model
        device = settings.faster_whisper_device
        compute_type = settings.faster_whisper_compute_type
        
        # Auto-detect GPU
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
        
        logger.info("Loading faster-whisper model", model=model_name, device=device)
        self._faster_whisper_model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
    
    segments, info = self._faster_whisper_model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,  # Enable VAD for better accuracy
    )
    
    return self._parse_faster_whisper_result(segments, info)
```

- [ ] **Step 3: Update smart routing to use faster-whisper**

```python
# In core/smart_transcriber.py:
def _get_whisper_transcriber(self) -> Transcriber:
    """Get Whisper transcriber (uses faster-whisper if available)."""
    if self._whisper_transcriber is None:
        logger.info("Initializing faster-whisper transcriber")
        self._whisper_transcriber = Transcriber(provider=STTProvider.FASTER_WHISPER)
    return self._whisper_transcriber
```

- [ ] **Step 4: Test faster-whisper integration**

Run: `pytest tests/test_faster_whisper.py -v`
Expected: faster-whisper loads and transcribes faster than standard Whisper

- [ ] **Step 5: Commit**

```bash
git add config/settings.py core/transcriber.py core/smart_transcriber.py
git commit -m "feat: integrate faster-whisper for 3-5x performance improvement"
```

---

### Task 4: Optimize SenseVoice Performance

**Files:**
- Modify: `core/transcriber.py:199-258`
- Test: `tests/test_sensevoice_perf.py`

**Problem:** SenseVoice on CPU is slow for long audio.

**Solution:** Add batch processing and VAD optimization.

- [ ] **Step 1: Optimize SenseVoice parameters**

```python
# In core/transcriber.py:
def _transcribe_with_sensevoice(self, audio_path, language):
    # ... existing code ...
    
    # Optimize parameters for speed
    res = self._sensevoice_model.generate(
        input=str(audio_path),
        cache={},
        language=sv_language,
        use_itn=True,
        batch_size_s=120,  # Increased from 60 for better throughput
        merge_vad=True,
        merge_length_s=15,
        # Add VAD parameters for long audio
        vad_kwargs={
            "max_single_segment_time": 30000,
            "min_single_segment_time": 5000,  # NEW: Avoid too short segments
        },
    )
    
    return self._parse_sensevoice_result(res)
```

- [ ] **Step 2: Add GPU detection for SenseVoice**

```python
# In core/transcriber.py:
def _transcribe_with_sensevoice(self, audio_path, language):
    # ... existing code ...
    
    if self._sensevoice_model is None:
        import torch
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        logger.info("Loading SenseVoice model", device=device)
        self._sensevoice_model = AutoModel(
            model="iic/SenseVoiceSmall",
            trust_remote_code=True,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device=device,  # Will use CUDA if available
        )
    
    # ... rest of code
```

- [ ] **Step 3: Test SenseVoice performance**

Run: `pytest tests/test_sensevoice_perf.py -v`
Expected: SenseVoice uses GPU if available, processes audio faster

- [ ] **Step 4: Commit**

```bash
git add core/transcriber.py
git commit -m "perf: optimize SenseVoice with GPU detection and VAD tuning"
```

---

## Phase 3: UX Improvements (P1 - User Experience)

### Task 5: Real-time Progress Updates

**Files:**
- Modify: `backend/routers/transcribe.py:233-283`
- Create: `src/components/TranscriptionProgress.tsx`
- Modify: `src/app/dashboard/library/page.tsx`
- Test: `tests/test_progress_updates.py`

**Problem:** Progress bar stuck at 20% for hours.

**Solution:** Implement progress callback mechanism with time-based estimates.

- [ ] **Step 1: Add progress callback to transcription**

```python
# In backend/routers/transcribe.py:
import threading
import time

def _do_transcription(task_id, file_path, title, force_engine):
    try:
        jobs[task_id]["status"] = "processing"
        jobs[task_id]["progress"] = 5.0
        
        # Create episode
        episode = PodcastEpisode(
            title=title,
            audio_url="",
            local_audio_path=file_path,
        )
        
        jobs[task_id]["progress"] = 10.0
        
        # Get audio duration for progress calculation
        duration = get_audio_duration(file_path)
        
        # Start progress updater thread
        stop_progress = threading.Event()
        
        def update_progress():
            """Update progress based on elapsed time vs estimate."""
            start_time = time.time()
            while not stop_progress.is_set():
                elapsed = time.time() - start_time
                if duration and jobs[task_id].get("estimate"):
                    total_estimate = jobs[task_id]["estimate"]["total_seconds"]
                    # Progress from 10% to 90% based on time
                    progress = 10 + min(80, (elapsed / total_estimate) * 80)
                    jobs[task_id]["progress"] = round(progress, 1)
                time.sleep(5)  # Update every 5 seconds
        
        progress_thread = threading.Thread(target=update_progress)
        progress_thread.start()
        
        try:
            # Run transcription
            transcriber = SmartTranscriber()
            transcript = transcriber.transcribe(episode, force_engine=force_engine)
            
            # Success
            jobs[task_id]["status"] = "completed"
            jobs[task_id]["progress"] = 100.0
            
        finally:
            stop_progress.set()
            progress_thread.join(timeout=1)
        
    except Exception as e:
        category, message = _categorize_error(e)
        jobs[task_id]["status"] = "failed"
        jobs[task_id]["error"] = message
        jobs[task_id]["error_category"] = category
```

- [ ] **Step 2: Create real-time progress component**

```tsx
// In src/components/TranscriptionProgress.tsx:
"use client";

import { motion } from "framer-motion";
import { Loader2, Clock, AlertCircle, CheckCircle } from "lucide-react";

interface TranscriptionProgressProps {
  progress: number;
  status: string;
  estimate?: { formatted_time: string } | null;
  elapsedSeconds?: number | null;
  remainingSeconds?: number | null;
}

export default function TranscriptionProgress({
  progress,
  status,
  estimate,
  elapsedSeconds,
  remainingSeconds,
}: TranscriptionProgressProps) {
  const isProcessing = status === "processing" || status === "pending";
  const isCompleted = status === "completed";
  const isFailed = status === "failed";
  
  // Calculate smooth progress for display
  const displayProgress = Math.min(99, Math.max(5, progress));
  
  return (
    <div className="w-full">
      {/* Status indicator */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isProcessing && (
            <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
          )}
          {isCompleted && (
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          )}
          {isFailed && (
            <AlertCircle className="w-4 h-4 text-red-400" />
          )}
          <span className={`text-sm ${
            isProcessing ? "text-amber-400" :
            isCompleted ? "text-emerald-400" :
            isFailed ? "text-red-400" : "text-gray-400"
          }`}>
            {isProcessing ? "转录中" :
             isCompleted ? "转录完成" :
             isFailed ? "转录失败" : "等待中"}
          </span>
        </div>
        
        {/* Time estimate */}
        {isProcessing && (remainingSeconds !== null || estimate) && (
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Clock className="w-3 h-3" />
            <span>
              {remainingSeconds !== null && remainingSeconds > 0
                ? `剩余约 ${Math.ceil(remainingSeconds / 60)} 分钟`
                : estimate?.formatted_time
                  ? `预估 ${estimate.formatted_time}`
                  : "计算中..."
              }
            </span>
          </div>
        )}
      </div>
      
      {/* Progress bar */}
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${
            isFailed ? "bg-red-500" :
            isCompleted ? "bg-emerald-500" :
            "bg-amber-500"
          }`}
          initial={{ width: 0 }}
          animate={{ width: `${displayProgress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
      
      {/* Percentage */}
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-600">{displayProgress.toFixed(0)}%</span>
        {elapsedSeconds !== null && (
          <span className="text-xs text-gray-600">
            已用 {Math.floor(elapsedSeconds / 60)} 分钟
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Integrate progress component into library page**

```tsx
// In src/app/dashboard/library/page.tsx:
// Replace existing progress display with TranscriptionProgress component

import TranscriptionProgress from "@/components/TranscriptionProgress";

// In the task display section:
{task && (
  <div className="mt-3 pt-3 border-t border-white/[0.04]">
    <TranscriptionProgress
      progress={task.progress}
      status={task.status}
      estimate={task.estimate}
      elapsedSeconds={task.elapsedSeconds}
      remainingSeconds={task.remainingSeconds}
    />
    
    {/* Error details */}
    {task.status === "failed" && (
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: "auto", opacity: 1 }}
        className="mt-3 overflow-hidden"
      >
        <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl">
          <p className="text-xs text-red-400 mb-1">{task.error}</p>
          <p className="text-xs text-gray-500">
            {getErrorSuggestion(task.errorCategory)}
          </p>
        </div>
      </motion.div>
    )}
  </div>
)}
```

- [ ] **Step 4: Test progress updates**

Run: `pytest tests/test_progress_updates.py -v`
Expected: Progress updates every 5 seconds, smooth animation

- [ ] **Step 5: Commit**

```bash
git add backend/routers/transcribe.py src/components/TranscriptionProgress.tsx src/app/dashboard/library/page.tsx
git commit -m "feat: real-time progress updates with time estimates"
```

---

### Task 6: Improve Time Estimate Accuracy

**Files:**
- Modify: `backend/routers/transcribe.py:124-178`
- Test: `tests/test_time_estimates.py`

**Problem:** Time estimates are wildly inaccurate (shows 1h21m, takes 3-5h).

**Solution:** Use historical data and hardware detection for better estimates.

- [ ] **Step 1: Add hardware-aware estimation**

```python
# In backend/routers/transcribe.py:
import torch

def get_hardware_info() -> dict:
    """Get hardware capabilities for estimation."""
    info = {
        "has_cuda": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cpu_count": os.cpu_count(),
    }
    return info

def calculate_estimate_time(duration_seconds: float, provider: str = "sensevoice") -> dict:
    """Calculate accurate transcription estimate based on hardware."""
    hardware = get_hardware_info()
    
    # Base speed factors (relative to real-time)
    SPEED_FACTORS = {
        "sensevoice": {
            "cuda": 0.3,      # 3.3x real-time on GPU
            "cpu": 3.0,       # 0.33x real-time on CPU
        },
        "whisper": {
            "cuda": 0.5,
            "cpu": 5.0,
        },
        "faster_whisper": {
            "cuda": 0.15,     # 6.7x real-time on GPU
            "cpu": 1.5,       # 0.67x real-time on CPU
        },
    }
    
    # Determine device
    device = "cuda" if hardware["has_cuda"] else "cpu"
    
    # Get speed factor
    provider_speeds = SPEED_FACTORS.get(provider, SPEED_FACTORS["sensevoice"])
    factor = provider_speeds.get(device, provider_speeds["cpu"])
    
    # Calculate total time
    processing_time = duration_seconds * factor
    
    # Add overhead based on provider
    overhead = {
        "sensevoice": 30 if device == "cpu" else 10,
        "whisper": 60 if device == "cpu" else 15,
        "faster_whisper": 20 if device == "cpu" else 5,
    }.get(provider, 30)
    
    total_seconds = int(processing_time + overhead)
    
    # Format time
    if total_seconds < 60:
        formatted = f"{total_seconds}秒"
    elif total_seconds < 3600:
        mins = total_seconds // 60
        secs = total_seconds % 60
        formatted = f"{mins}分{secs}秒" if secs > 0 else f"{mins}分钟"
    else:
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        formatted = f"{hours}小时{mins}分" if mins > 0 else f"{hours}小时"
    
    return {
        "total_seconds": total_seconds,
        "formatted_time": formatted,
        "provider": provider,
        "device": device,
        "audio_duration_seconds": duration_seconds,
        "speed_factor": factor,
    }
```

- [ ] **Step 2: Test estimate accuracy**

Run: `pytest tests/test_time_estimates.py -v`
Expected: Estimates within 20% of actual time

- [ ] **Step 3: Commit**

```bash
git add backend/routers/transcribe.py
git commit -m "feat: hardware-aware time estimates with GPU detection"
```

---

## Phase 4: Testing and Validation (P1 - Quality Assurance)

### Task 7: Comprehensive Test Suite

**Files:**
- Create: `tests/test_transcription_integration.py`
- Create: `tests/test_performance_benchmarks.py`
- Create: `tests/test_accessibility.py`
- Modify: `pytest.ini`

**Goal:** Ensure 99.9% uptime and <5% error rate.

- [ ] **Step 1: Create integration tests**

```python
# In tests/test_transcription_integration.py:
import pytest
import time
from pathlib import Path

class TestTranscriptionIntegration:
    """Integration tests for transcription workflow."""
    
    @pytest.fixture
    def sample_audio_5min(self):
        """5-minute test audio file."""
        return Path("tests/fixtures/sample_5min_zh.mp3")
    
    @pytest.fixture
    def sample_audio_1hour(self):
        """1-hour test audio file."""
        return Path("tests/fixtures/sample_1h_en.mp3")
    
    def test_chinese_transcription_5min(self, client, sample_audio_5min):
        """Test Chinese transcription completes in <3 minutes."""
        start = time.time()
        
        response = client.post(
            "/api/transcribe/",
            files={"audio": sample_audio_5min.open("rb")}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Poll for completion
        max_wait = 180  # 3 minutes
        while time.time() - start < max_wait:
            status = client.get(f"/api/transcribe/{task_id}")
            if status.json()["status"] == "completed":
                break
            time.sleep(2)
        
        elapsed = time.time() - start
        assert elapsed < 180, f"Transcription took {elapsed}s, expected <180s"
        
        result = status.json()["result"]
        assert result["word_count"] > 100
        assert result["language"] == "zh"
    
    def test_english_transcription_5min(self, client, sample_audio_5min):
        """Test English transcription completes successfully."""
        response = client.post(
            "/api/transcribe/",
            files={"audio": sample_audio_5min.open("rb")}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Wait for completion
        max_wait = 180
        start = time.time()
        while time.time() - start < max_wait:
            status = client.get(f"/api/transcribe/{task_id}")
            if status.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(2)
        
        result = status.json()
        assert result["status"] == "completed", f"English transcription failed: {result.get('error')}"
    
    def test_progress_updates(self, client, sample_audio_5min):
        """Test progress updates are frequent and smooth."""
        response = client.post(
            "/api/transcribe/",
            files={"audio": sample_audio_5min.open("rb")}
        )
        
        task_id = response.json()["task_id"]
        
        # Collect progress updates
        progress_values = []
        start = time.time()
        while time.time() - start < 60:
            status = client.get(f"/api/transcribe/{task_id}")
            progress = status.json().get("progress", 0)
            progress_values.append(progress)
            
            if status.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(1)
        
        # Check progress is monotonic
        assert all(progress_values[i] <= progress_values[i+1] 
                  for i in range(len(progress_values)-1))
        
        # Check at least 5 updates
        assert len(set(progress_values)) >= 5, "Too few progress updates"
    
    def test_error_handling_file_not_found(self, client):
        """Test proper error for missing file."""
        response = client.post(
            "/api/transcribe/by-path",
            json={"file_path": "/nonexistent/file.mp3"}
        )
        
        assert response.status_code == 400
        assert "file_not_found" in response.json()["detail"]
```

- [ ] **Step 2: Create performance benchmarks**

```python
# In tests/test_performance_benchmarks.py:
import pytest
import time
import statistics

class TestPerformanceBenchmarks:
    """Performance benchmarks for transcription."""
    
    def test_transcription_speed_chinese(self, client, sample_audio_5min):
        """Benchmark Chinese transcription speed."""
        times = []
        
        for _ in range(3):  # Run 3 times
            start = time.time()
            response = client.post("/api/transcribe/", files={"audio": sample_audio_5min.open("rb")})
            task_id = response.json()["task_id"]
            
            # Wait for completion
            while True:
                status = client.get(f"/api/transcribe/{task_id}")
                if status.json()["status"] in ["completed", "failed"]:
                    break
                time.sleep(1)
            
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        assert avg_time < 180, f"Average time {avg_time}s exceeds 180s target"
        
        # Calculate real-time factor
        audio_duration = 300  # 5 minutes = 300 seconds
        rtf = avg_time / audio_duration
        assert rtf < 1.0, f"Real-time factor {rtf} exceeds 1.0 (slower than real-time)"
    
    def test_concurrent_transcriptions(self, client, sample_audio_5min):
        """Test system handles concurrent requests."""
        import concurrent.futures
        
        def transcribe():
            response = client.post("/api/transcribe/", files={"audio": sample_audio_5min.open("rb")})
            return response.json()["task_id"]
        
        # Submit 2 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(transcribe) for _ in range(2)]
            task_ids = [f.result() for f in futures]
        
        # Both should succeed
        for task_id in task_ids:
            max_wait = 300
            start = time.time()
            while time.time() - start < max_wait:
                status = client.get(f"/api/transcribe/{task_id}")
                if status.json()["status"] in ["completed", "failed"]:
                    break
                time.sleep(2)
            
            assert status.json()["status"] == "completed"
```

- [ ] **Step 3: Create accessibility tests**

```python
# In tests/test_accessibility.py:
import pytest

class TestAccessibility:
    """Accessibility tests for transcription UI."""
    
    def test_progress_bar_aria_labels(self, client):
        """Test progress bar has proper ARIA labels."""
        # This would be tested with a browser automation tool
        # For now, verify the component structure
        pass
    
    def test_error_messages_readable(self, client):
        """Test error messages are clear and actionable."""
        response = client.post(
            "/api/transcribe/by-path",
            json={"file_path": "/nonexistent/file.mp3"}
        )
        
        error = response.json()["detail"]
        assert len(error) < 200  # Concise
        assert "解决方案" in error or "请" in error  # Actionable
```

- [ ] **Step 4: Update pytest configuration**

```ini
# In pytest.ini:
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    performance: marks tests as performance benchmarks
```

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v -m "not slow"`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add tests/ pytest.ini
git commit -m "test: comprehensive test suite for transcription functionality"
```

---

### Task 8: Performance Monitoring

**Files:**
- Create: `utils/metrics.py`
- Modify: `backend/routers/transcribe.py`
- Create: `scripts/generate_metrics_report.py`

**Goal:** Track and report performance metrics over time.

- [ ] **Step 1: Create metrics collection module**

```python
# In utils/metrics.py:
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class TranscriptionMetrics:
    """Metrics for a single transcription job."""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    audio_duration_seconds: Optional[float] = None
    provider: str = "unknown"
    device: str = "cpu"
    status: str = "pending"
    error_category: Optional[str] = None
    word_count: Optional[int] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def real_time_factor(self) -> Optional[float]:
        if self.duration_seconds and self.audio_duration_seconds:
            return self.duration_seconds / self.audio_duration_seconds
        return None

class MetricsCollector:
    """Collect and report transcription metrics."""
    
    def __init__(self, metrics_file: Path = Path("data/metrics/transcription.jsonl")):
        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_jobs: dict[str, TranscriptionMetrics] = {}
    
    def start_job(self, task_id: str, audio_duration: Optional[float] = None, provider: str = "unknown") -> None:
        """Record job start."""
        self._current_jobs[task_id] = TranscriptionMetrics(
            task_id=task_id,
            start_time=time.time(),
            audio_duration_seconds=audio_duration,
            provider=provider,
        )
    
    def end_job(self, task_id: str, status: str, word_count: Optional[int] = None, error_category: Optional[str] = None) -> None:
        """Record job completion."""
        if task_id not in self._current_jobs:
            return
        
        metrics = self._current_jobs[task_id]
        metrics.end_time = time.time()
        metrics.status = status
        metrics.word_count = word_count
        metrics.error_category = error_category
        
        # Save to file
        self._save_metrics(metrics)
        
        # Clean up
        del self._current_jobs[task_id]
    
    def _save_metrics(self, metrics: TranscriptionMetrics) -> None:
        """Append metrics to file."""
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")
    
    def get_summary(self, days: int = 7) -> dict:
        """Get metrics summary for last N days."""
        if not self.metrics_file.exists():
            return {}
        
        cutoff = time.time() - (days * 24 * 3600)
        
        jobs = []
        with open(self.metrics_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data["start_time"] > cutoff:
                    jobs.append(data)
        
        if not jobs:
            return {}
        
        total = len(jobs)
        completed = sum(1 for j in jobs if j["status"] == "completed")
        failed = sum(1 for j in jobs if j["status"] == "failed")
        
        durations = [j["end_time"] - j["start_time"] for j in jobs if j["end_time"]]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        rtfs = []
        for j in jobs:
            if j["end_time"] and j["audio_duration_seconds"]:
                rtf = (j["end_time"] - j["start_time"]) / j["audio_duration_seconds"]
                rtfs.append(rtf)
        avg_rtf = sum(rtfs) / len(rtfs) if rtfs else 0
        
        return {
            "period_days": days,
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "avg_duration_seconds": avg_duration,
            "avg_real_time_factor": avg_rtf,
            "uptime_percentage": (completed / total * 100) if total > 0 else 0,
        }

# Global instance
metrics_collector = MetricsCollector()
```

- [ ] **Step 2: Integrate metrics into transcription router**

```python
# In backend/routers/transcribe.py:
from utils.metrics import metrics_collector

def _do_transcription(task_id, file_path, title, force_engine):
    # ... existing code ...
    
    # Get audio duration for metrics
    duration = get_audio_duration(file_path)
    provider = "sensevoice"  # or detect from engine used
    
    # Start metrics collection
    metrics_collector.start_job(task_id, duration, provider)
    
    try:
        # ... transcription logic ...
        
        # Success
        metrics_collector.end_job(
            task_id=task_id,
            status="completed",
            word_count=transcript.word_count,
        )
        
    except Exception as e:
        category, _ = _categorize_error(e)
        metrics_collector.end_job(
            task_id=task_id,
            status="failed",
            error_category=category,
        )
```

- [ ] **Step 3: Create metrics report script**

```python
# In scripts/generate_metrics_report.py:
#!/usr/bin/env python3
"""Generate transcription metrics report."""

import json
from datetime import datetime
from utils.metrics import metrics_collector

def main():
    summary = metrics_collector.get_summary(days=7)
    
    print("=" * 60)
    print("TRANSCRIPTION METRICS REPORT")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 60)
    
    if not summary:
        print("No metrics data available.")
        return
    
    print(f"\nPeriod: Last {summary['period_days']} days")
    print(f"Total Jobs: {summary['total_jobs']}")
    print(f"Completed: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1%}")
    print(f"Uptime: {summary['uptime_percentage']:.1f}%")
    
    if summary['avg_duration_seconds'] > 0:
        avg_mins = summary['avg_duration_seconds'] / 60
        print(f"Avg Duration: {avg_mins:.1f} minutes")
    
    if summary['avg_real_time_factor'] > 0:
        print(f"Avg Real-time Factor: {summary['avg_real_time_factor']:.2f}x")
        if summary['avg_real_time_factor'] < 1.0:
            speedup = 1.0 / summary['avg_real_time_factor']
            print(f"  (Processing is {speedup:.1f}x faster than real-time)")
        else:
            print(f"  (Processing is {summary['avg_real_time_factor']:.1f}x slower than real-time)")
    
    print("\n" + "=" * 60)
    
    # Check against targets
    print("\nTARGETS:")
    targets = {
        "Uptime >= 99.9%": summary['uptime_percentage'] >= 99.9,
        "Success Rate >= 95%": summary['success_rate'] >= 0.95,
        "RTF < 1.0 (faster than real-time)": summary.get('avg_real_time_factor', 999) < 1.0,
    }
    
    for target, met in targets.items():
        status = "✅ PASS" if met else "❌ FAIL"
        print(f"  {status}: {target}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test metrics collection**

Run: `python scripts/generate_metrics_report.py`
Expected: Report shows current metrics status

- [ ] **Step 5: Commit**

```bash
git add utils/metrics.py backend/routers/transcribe.py scripts/generate_metrics_report.py
git commit -m "feat: add performance metrics collection and reporting"
```

---

## Success Criteria

### Performance Targets

| Metric | Before | Target | After |
|--------|--------|--------|-------|
| English transcription success | 0% | 99.9% | TBD |
| Chinese transcription (1h audio) | 3-5 hours | <15 min | TBD |
| Real-time factor (RTF) | >3.0 | <1.0 | TBD |
| Progress update frequency | 3 total | Every 5% | TBD |
| Estimate accuracy | ~30% | >90% | TBD |
| System uptime | Unknown | 99.9% | TBD |
| Error rate | Unknown | <5% | TBD |

### Accessibility Targets

- [ ] Progress bar has ARIA labels
- [ ] Error messages are actionable
- [ ] Color contrast meets WCAG 2.1 AA
- [ ] Keyboard navigation works
- [ ] Screen reader compatible

### Testing Coverage

- [ ] Unit tests: >80% coverage
- [ ] Integration tests: All critical paths
- [ ] Performance benchmarks: Baseline established
- [ ] Accessibility tests: WCAG 2.1 AA compliance

---

## Rollback Plan

If issues arise during deployment:

1. **Immediate rollback**: Revert to previous git commit
2. **Feature flags**: Disable faster-whisper, fall back to SenseVoice
3. **Monitoring alerts**: Notify if success rate drops below 95%
4. **Manual override**: Allow users to select specific engine

---

## Timeline

| Phase | Tasks | Duration | Dependencies |
|-------|-------|----------|--------------|
| Phase 1 | Tasks 1-2 | 1-2 days | None |
| Phase 2 | Tasks 3-4 | 2-3 days | Phase 1 |
| Phase 3 | Tasks 5-6 | 2-3 days | Phase 2 |
| Phase 4 | Tasks 7-8 | 2-3 days | Phase 3 |
| **Total** | | **7-11 days** | |

---

## Documentation

- [ ] Update API documentation
- [ ] Update user guide with new features
- [ ] Document performance benchmarks
- [ ] Create troubleshooting guide
- [ ] Add metrics dashboard documentation
