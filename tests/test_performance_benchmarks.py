"""转录性能基准测试.

测试转录系统的性能指标，包括：
- 转录速度（实时因子 RTF）
- 并发处理能力
- 内存使用
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest


class TestPerformanceBenchmarks:
    """性能基准测试."""

    @pytest.fixture
    def sample_audio_zh(self):
        """中文测试音频文件."""
        return Path("data/audio/港股的特殊之处与生存之道.mp3")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_transcription_speed_sensevoice(self, client, sample_audio_zh):
        """基准测试：SenseVoice 转录速度.

        目标：5 分钟音频在 3 分钟内完成（RTF < 1.0）
        """
        if not sample_audio_zh.exists():
            pytest.skip("测试音频文件不存在")

        times = []

        for i in range(2):  # 运行 2 次取平均
            start = time.time()
            response = client.post(
                "/api/transcribe/",
                files={"audio": sample_audio_zh.open("rb")},
            )

            assert response.status_code == 200
            task_id = response.json()["task_id"]

            # 等待完成
            max_wait = 300
            wait_start = time.time()
            while time.time() - wait_start < max_wait:
                status = client.get(f"/api/transcribe/{task_id}")
                if status.json()["status"] in ["completed", "failed"]:
                    break
                time.sleep(2)

            elapsed = time.time() - start
            times.append(elapsed)

            # 清理，避免影响下一次测试
            if status.json()["status"] == "completed":
                result = status.json().get("result", {})
                audio_duration = result.get("duration_seconds", 0)
                if audio_duration > 0:
                    rtf = elapsed / audio_duration
                    pytest.rtf_record = rtf  # 记录 RTF 供分析

        avg_time = statistics.mean(times)

        # 断言：平均时间应小于 180 秒（3 分钟）
        assert avg_time < 180, (
            f"平均转录时间 {avg_time:.1f}s 超过 180s 目标"
        )

    @pytest.mark.performance
    def test_time_estimate_accuracy(self, client, sample_audio_zh):
        """测试时间预估准确性.

        目标：预估时间与实际时间误差 < 50%
        """
        if not sample_audio_zh.exists():
            pytest.skip("测试音频文件不存在")

        start = time.time()
        response = client.post(
            "/api/transcribe/",
            files={"audio": sample_audio_zh.open("rb")},
        )

        assert response.status_code == 200
        data = response.json()
        task_id = data["task_id"]
        estimate_seconds = data.get("estimate", {}).get("total_seconds", 0)

        # 等待完成
        max_wait = 300
        wait_start = time.time()
        while time.time() - wait_start < max_wait:
            status = client.get(f"/api/transcribe/{task_id}")
            if status.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(2)

        actual_seconds = time.time() - start

        if estimate_seconds > 0 and status.json()["status"] == "completed":
            error_ratio = abs(actual_seconds - estimate_seconds) / estimate_seconds
            assert error_ratio < 0.5, (
                f"时间预估误差 {error_ratio:.1%} 超过 50%，"
                f"预估: {estimate_seconds}s, 实际: {actual_seconds:.0f}s"
            )

    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_transcriptions(self, client, sample_audio_zh):
        """测试并发转录处理能力.

        目标：2 个并发任务都能成功完成
        """
        if not sample_audio_zh.exists():
            pytest.skip("测试音频文件不存在")

        import concurrent.futures

        def transcribe():
            response = client.post(
                "/api/transcribe/",
                files={"audio": sample_audio_zh.open("rb")},
            )
            return response.json()["task_id"]

        # 提交 2 个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(transcribe) for _ in range(2)]
            task_ids = [f.result() for f in futures]

        # 验证两个任务都成功
        for task_id in task_ids:
            max_wait = 300
            start = time.time()
            while time.time() - start < max_wait:
                status = client.get(f"/api/transcribe/{task_id}")
                if status.json()["status"] in ["completed", "failed"]:
                    break
                time.sleep(2)

            assert status.json()["status"] == "completed", (
                f"并发任务 {task_id} 失败: {status.json().get('error')}"
            )

    def test_progress_update_frequency(self, client, sample_audio_zh):
        """测试进度更新频率.

        目标：60 秒内至少 5 次进度更新
        """
        if not sample_audio_zh.exists():
            pytest.skip("测试音频文件不存在")

        response = client.post(
            "/api/transcribe/",
            files={"audio": sample_audio_zh.open("rb")},
        )

        assert response.status_code == 200
        task_id = response.json()["task_id"]

        # 收集进度更新
        progress_values = []
        start = time.time()

        while time.time() - start < 60:
            status = client.get(f"/api/transcribe/{task_id}")
            progress = status.json().get("progress", 0)
            progress_values.append(progress)

            if status.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(1)

        # 验证至少 5 次不同的进度更新
        unique_updates = len(set(progress_values))
        assert unique_updates >= 5, (
            f"进度更新次数 {unique_updates} 少于 5 次"
        )

    def test_hardware_aware_estimate_variation(self):
        """测试硬件感知预估的差异性."""
        from backend.routers.transcribe import calculate_estimate_time

        # 同一音频，不同引擎的预估应该不同
        duration = 3600  # 1 小时

        estimate_sv = calculate_estimate_time(duration, "sensevoice")
        estimate_fw = calculate_estimate_time(duration, "faster_whisper")

        # faster-whisper 应该比 SenseVoice 快（总时间更短）
        assert estimate_fw["total_seconds"] < estimate_sv["total_seconds"], (
            "faster-whisper 预估不应慢于 SenseVoice"
        )

    def test_estimate_formatting(self):
        """测试时间格式化正确性."""
        from backend.routers.transcribe import calculate_estimate_time

        # 测试秒级
        est1 = calculate_estimate_time(30, "sensevoice")
        assert "秒" in est1["formatted_time"] or "分钟" in est1["formatted_time"]

        # 测试分钟级
        est2 = calculate_estimate_time(300, "sensevoice")
        assert "分钟" in est2["formatted_time"] or "分" in est2["formatted_time"]

        # 测试小时级
        est3 = calculate_estimate_time(3600, "sensevoice")
        assert "小时" in est3["formatted_time"] or "时" in est3["formatted_time"]
