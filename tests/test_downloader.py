"""音频下载模块测试."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from core.audio_downloader import AudioDownloader, RSSParseError
from models.podcast import PodcastEpisode, PodcastFeed


class TestAudioDownloader:
    """音频下载器测试类."""

    @pytest.fixture
    def downloader(self, tmp_path: Path) -> AudioDownloader:
        """创建测试用的下载器实例."""
        return AudioDownloader(download_dir=tmp_path / "audio")

    def test_parse_duration_hhmmss(self, downloader: AudioDownloader) -> None:
        """测试 HH:MM:SS 格式时长解析."""
        assert downloader._parse_duration("1:23:45") == 5025

    def test_parse_duration_mmss(self, downloader: AudioDownloader) -> None:
        """测试 MM:SS 格式时长解析."""
        assert downloader._parse_duration("12:34") == 754

    def test_parse_duration_seconds(self, downloader: AudioDownloader) -> None:
        """测试纯秒数格式时长解析."""
        assert downloader._parse_duration("3600") == 3600

    def test_parse_duration_invalid(self, downloader: AudioDownloader) -> None:
        """测试无效时长解析."""
        assert downloader._parse_duration("invalid") is None
        assert downloader._parse_duration("") is None

    def test_extract_episode_number_chinese(self, downloader: AudioDownloader) -> None:
        """测试中文集数提取."""
        assert downloader._extract_episode_number("第123期：测试标题") == 123
        assert downloader._extract_episode_number("第 45 集 测试") == 45

    def test_extract_episode_number_ep(self, downloader: AudioDownloader) -> None:
        """测试 EP 格式集数提取."""
        assert downloader._extract_episode_number("EP12: Test Title") == 12
        assert downloader._extract_episode_number("ep 99 测试") == 99

    def test_extract_episode_number_hash(self, downloader: AudioDownloader) -> None:
        """测试 # 格式集数提取."""
        assert downloader._extract_episode_number("#100 测试标题") == 100

    def test_extract_episode_number_none(self, downloader: AudioDownloader) -> None:
        """测试无集数的情况."""
        assert downloader._extract_episode_number("没有集数的标题") is None

    def test_load_local_audio_success(self, downloader: AudioDownloader, tmp_path: Path) -> None:
        """测试成功加载本地音频."""
        audio_file = tmp_path / "test_audio.mp3"
        audio_file.write_text("fake audio content")

        episode = downloader.load_local_audio(audio_file)

        assert episode.title == "test_audio"
        assert episode.local_audio_path == audio_file
        assert episode.audio_url == str(audio_file)

    def test_load_local_audio_not_found(self, downloader: AudioDownloader) -> None:
        """测试加载不存在的音频文件."""
        from core.audio_downloader import AudioDownloaderError

        with pytest.raises(AudioDownloaderError, match="音频文件不存在"):
            downloader.load_local_audio("/nonexistent/file.mp3")


class TestPodcastEpisode:
    """播客单集模型测试."""

    def test_get_safe_filename_with_episode(self) -> None:
        """测试带集数的安全文件名生成."""
        episode = PodcastEpisode(
            title="测试标题！带有特殊字符@#",
            audio_url="http://example.com/audio.mp3",
            episode_number=42,
            feed_title="测试播客",
        )
        assert episode.get_safe_filename() == "ep042_测试标题带有特殊字符"

    def test_get_safe_filename_without_episode(self) -> None:
        """测试不带集数的安全文件名生成."""
        episode = PodcastEpisode(
            title="简单标题",
            audio_url="http://example.com/audio.mp3",
        )
        assert episode.get_safe_filename() == "简单标题"

    def test_str_representation(self) -> None:
        """测试字符串表示."""
        episode = PodcastEpisode(
            title="测试单集",
            audio_url="http://example.com/audio.mp3",
            episode_number=1,
            feed_title="测试播客",
        )
        assert str(episode) == "《测试播客》第1期: 测试单集"


class TestPodcastFeed:
    """播客订阅源模型测试."""

    def test_get_latest_episode(self) -> None:
        """测试获取最新单集."""
        feed = PodcastFeed(
            title="测试播客",
            url="http://example.com/feed.xml",
            episodes=[
                PodcastEpisode(
                    title="旧单集",
                    audio_url="http://example.com/old.mp3",
                    publish_date=datetime(2024, 1, 1),
                ),
                PodcastEpisode(
                    title="新单集",
                    audio_url="http://example.com/new.mp3",
                    publish_date=datetime(2024, 6, 1),
                ),
            ],
        )
        latest = feed.get_latest_episode()
        assert latest is not None
        assert latest.title == "新单集"

    def test_get_latest_episode_empty(self) -> None:
        """测试空播客获取最新单集."""
        feed = PodcastFeed(
            title="空播客",
            url="http://example.com/feed.xml",
        )
        assert feed.get_latest_episode() is None
