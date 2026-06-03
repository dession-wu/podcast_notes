"""性能指标收集模块.

用于收集和报告转录性能指标，支持：
- 任务开始/结束记录
- 实时因子（RTF）计算
- 成功率统计
- 生成报告
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TranscriptionMetrics:
    """单个转录任务的指标."""

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
        """计算任务持续时间."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

    @property
    def real_time_factor(self) -> Optional[float]:
        """计算实时因子（RTF）.

        RTF = 处理时间 / 音频时长
        RTF < 1.0 表示快于实时
        """
        if self.duration_seconds and self.audio_duration_seconds:
            return self.duration_seconds / self.audio_duration_seconds
        return None


class MetricsCollector:
    """转录指标收集器."""

    def __init__(
        self,
        metrics_file: Path = Path("data/metrics/transcription.jsonl"),
    ) -> None:
        """初始化收集器.

        Args:
            metrics_file: 指标存储文件路径
        """
        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_jobs: dict[str, TranscriptionMetrics] = {}

    def start_job(
        self,
        task_id: str,
        audio_duration: Optional[float] = None,
        provider: str = "unknown",
        device: str = "cpu",
    ) -> None:
        """记录任务开始.

        Args:
            task_id: 任务 ID
            audio_duration: 音频时长（秒）
            provider: 使用的引擎
            device: 使用的设备
        """
        self._current_jobs[task_id] = TranscriptionMetrics(
            task_id=task_id,
            start_time=time.time(),
            audio_duration_seconds=audio_duration,
            provider=provider,
            device=device,
        )

    def end_job(
        self,
        task_id: str,
        status: str,
        word_count: Optional[int] = None,
        error_category: Optional[str] = None,
    ) -> None:
        """记录任务完成.

        Args:
            task_id: 任务 ID
            status: 任务状态 (completed/failed)
            word_count: 转录字数
            error_category: 错误类别
        """
        if task_id not in self._current_jobs:
            return

        metrics = self._current_jobs[task_id]
        metrics.end_time = time.time()
        metrics.status = status
        metrics.word_count = word_count
        metrics.error_category = error_category

        # 保存到文件
        self._save_metrics(metrics)

        # 清理
        del self._current_jobs[task_id]

    def _save_metrics(self, metrics: TranscriptionMetrics) -> None:
        """追加指标到文件.

        Args:
            metrics: 要保存的指标
        """
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")

    def get_summary(self, days: int = 7) -> dict:
        """获取最近 N 天的指标摘要.

        Args:
            days: 天数

        Returns:
            摘要字典
        """
        if not self.metrics_file.exists():
            return {}

        cutoff = time.time() - (days * 24 * 3600)

        jobs = []
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("start_time", 0) > cutoff:
                            jobs.append(data)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            return {}

        if not jobs:
            return {}

        total = len(jobs)
        completed = sum(1 for j in jobs if j.get("status") == "completed")
        failed = sum(1 for j in jobs if j.get("status") == "failed")

        # 计算平均持续时间
        durations = []
        for j in jobs:
            end = j.get("end_time")
            start = j.get("start_time")
            if end and start:
                durations.append(end - start)
        avg_duration = sum(durations) / len(durations) if durations else 0

        # 计算平均 RTF
        rtfs = []
        for j in jobs:
            end = j.get("end_time")
            start = j.get("start_time")
            audio_dur = j.get("audio_duration_seconds")
            if end and start and audio_dur and audio_dur > 0:
                rtf = (end - start) / audio_dur
                rtfs.append(rtf)
        avg_rtf = sum(rtfs) / len(rtfs) if rtfs else 0

        # 按引擎统计
        providers = {}
        for j in jobs:
            provider = j.get("provider", "unknown")
            if provider not in providers:
                providers[provider] = {"total": 0, "completed": 0, "failed": 0}
            providers[provider]["total"] += 1
            if j.get("status") == "completed":
                providers[provider]["completed"] += 1
            else:
                providers[provider]["failed"] += 1

        return {
            "period_days": days,
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "avg_duration_seconds": avg_duration,
            "avg_real_time_factor": avg_rtf,
            "uptime_percentage": (completed / total * 100) if total > 0 else 0,
            "providers": providers,
        }


# 全局实例
metrics_collector = MetricsCollector()
