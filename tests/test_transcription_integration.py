"""转录功能集成测试.

测试转录工作流的完整流程，包括：
- 中文/英文转录
- 进度更新
- 错误处理
- 并发处理
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest


class TestTranscriptionIntegration:
    """转录功能集成测试."""

    @pytest.fixture
    def sample_audio_zh(self):
        """中文测试音频文件."""
        return Path("data/audio/港股的特殊之处与生存之道.mp3")

    @pytest.fixture
    def sample_audio_en(self):
        """英文测试音频文件."""
        return Path("data/audio/ep236_236 Git Tips for Testing - Adam Johnson.mp3")

    def test_language_detector_english_routes_to_sensevoice(self):
        """测试英文语言检测路由到 SenseVoice."""
        from core.language_detector import LanguageDetector
        from models.podcast import PodcastEpisode

        detector = LanguageDetector()
        episode = PodcastEpisode(
            title="English Podcast Episode",
            audio_url="",
            local_audio_path=Path("test_en.mp3"),
        )

        result = detector.detect(episode)

        assert result["language"] == "en"
        assert result["engine"] == "sensevoice"
        assert result["method"] == "title"

    def test_language_detector_chinese_routes_to_sensevoice(self):
        """测试中文语言检测路由到 SenseVoice."""
        from core.language_detector import LanguageDetector
        from models.podcast import PodcastEpisode

        detector = LanguageDetector()
        episode = PodcastEpisode(
            title="中文播客节目",
            audio_url="",
            local_audio_path=Path("test_zh.mp3"),
        )

        result = detector.detect(episode)

        assert result["language"] == "zh"
        assert result["engine"] == "sensevoice"

    def test_error_categorization_model_not_installed(self):
        """测试模型未安装错误分类."""
        from backend.routers.transcribe import _categorize_error

        error = Exception("未安装 faster-whisper，请运行: pip install faster-whisper")
        category, message = _categorize_error(error)

        assert category == "model_not_installed"
        assert "未安装" in message

    def test_error_categorization_out_of_memory(self):
        """测试内存不足错误分类."""
        from backend.routers.transcribe import _categorize_error

        error = Exception("CUDA out of memory")
        category, message = _categorize_error(error)

        assert category == "out_of_memory"
        assert "内存不足" in message

    def test_error_categorization_timeout(self):
        """测试超时错误分类."""
        from backend.routers.transcribe import _categorize_error

        error = Exception("transcription timed out")
        category, message = _categorize_error(error)

        assert category == "timeout"
        assert "超时" in message

    def test_hardware_info_detection(self):
        """测试硬件信息检测."""
        from backend.routers.transcribe import get_hardware_info

        info = get_hardware_info()

        assert "has_cuda" in info
        assert "cuda_device" in info
        assert "cpu_count" in info
        assert isinstance(info["has_cuda"], bool)
        assert isinstance(info["cpu_count"], int)

    def test_calculate_estimate_time_cpu(self):
        """测试 CPU 时间预估."""
        from backend.routers.transcribe import calculate_estimate_time

        # 模拟 CPU 环境（无 CUDA）
        estimate = calculate_estimate_time(3600, "sensevoice")

        assert "total_seconds" in estimate
        assert "formatted_time" in estimate
        assert "device" in estimate
        assert estimate["device"] == "cpu"
        assert estimate["speed_factor"] > 0

    def test_calculate_estimate_time_structure(self):
        """测试时间预估返回结构完整性."""
        from backend.routers.transcribe import calculate_estimate_time

        estimate = calculate_estimate_time(1800, "faster_whisper")

        required_keys = [
            "total_seconds",
            "formatted_time",
            "provider",
            "device",
            "audio_duration_seconds",
            "audio_duration_formatted",
            "speed_factor",
            "has_cuda",
        ]
        for key in required_keys:
            assert key in estimate, f"Missing key: {key}"

    @pytest.mark.slow
    def test_transcription_job_lifecycle(self, client, sample_audio_zh):
        """测试转录任务完整生命周期（慢速测试）."""
        if not sample_audio_zh.exists():
            pytest.skip("测试音频文件不存在")

        # 开始转录
        response = client.post(
            "/api/transcribe/",
            files={"audio": sample_audio_zh.open("rb")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "processing"

        task_id = data["task_id"]

        # 轮询状态
        max_wait = 300  # 5 分钟
        start = time.time()
        final_status = None

        while time.time() - start < max_wait:
            status_response = client.get(f"/api/transcribe/{task_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            final_status = status_data

            if status_data["status"] in ["completed", "failed"]:
                break

            # 验证进度更新
            if status_data["status"] == "processing":
                assert status_data.get("progress") is not None
                assert 0 <= status_data["progress"] <= 100

            time.sleep(2)

        # 验证最终结果
        assert final_status is not None
        assert final_status["status"] == "completed", (
            f"转录失败: {final_status.get('error')}"
        )

        if final_status.get("result"):
            assert "word_count" in final_status["result"]
            assert "language" in final_status["result"]

    def test_progress_updates_monotonic(self, client, sample_audio_zh):
        """测试进度更新是单调递增的."""
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

        # 验证进度单调递增
        for i in range(len(progress_values) - 1):
            assert progress_values[i] <= progress_values[i + 1], (
                f"进度回退: {progress_values[i]} -> {progress_values[i + 1]}"
            )

    def test_invalid_file_error(self, client):
        """测试无效文件错误处理."""
        response = client.post(
            "/api/transcribe/by-path",
            json={"file_path": "/nonexistent/file.mp3"},
        )

        assert response.status_code == 400

    def test_unsupported_format_error(self, client, tmp_path):
        """测试不支持格式错误处理."""
        # 创建一个假的 txt 文件
        fake_audio = tmp_path / "test.txt"
        fake_audio.write_text("not audio")

        response = client.post(
            "/api/transcribe/by-path",
            json={"file_path": str(fake_audio)},
        )

        assert response.status_code == 400
