"""播客主持人注册系统 — 说话人身份管理与识别.

支持：
- 播客主持人声音特征注册
- 说话人嵌入向量存储与检索
- 基于余弦相似度的说话人识别
- 跨期播客的说话人一致性管理
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from utils import get_logger

logger = get_logger(__name__)


class SpeakerRegistryError(Exception):
    """说话人注册系统错误."""

    pass


class SpeakerInfo:
    """说话人信息模型."""

    def __init__(
        self,
        speaker_id: str,
        name: str,
        embeddings: list[float] | None = None,
        podcast_name: str | None = None,
        role: str = "guest",
    ) -> None:
        """初始化说话人信息.

        Args:
            speaker_id: 说话人 ID（如 SPEAKER_0）
            name: 说话人名称
            embeddings: 声音特征嵌入向量
            podcast_name: 所属播客名称
            role: 角色（host/guest/co-host）
        """
        self.speaker_id = speaker_id
        self.name = name
        self.embeddings = embeddings or []
        self.podcast_name = podcast_name
        self.role = role

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "speaker_id": self.speaker_id,
            "name": self.name,
            "embeddings": self.embeddings,
            "podcast_name": self.podcast_name,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpeakerInfo":
        """从字典创建实例."""
        return cls(
            speaker_id=data["speaker_id"],
            name=data["name"],
            embeddings=data.get("embeddings"),
            podcast_name=data.get("podcast_name"),
            role=data.get("role", "guest"),
        )


class SpeakerRegistry:
    """说话人注册与管理器.

    管理播客主持人和嘉宾的声音特征，支持：
    - 注册新说话人
    - 通过嵌入向量识别说话人
    - 跨期播客的说话人一致性管理
    - 持久化存储
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """初始化说话人注册系统.

        Args:
            storage_path: 存储路径，默认使用 data/speakers/
        """
        self._storage_path = storage_path or (
            settings.data_dir / "speakers" / "registry.json"
        )
        self._speakers: dict[str, SpeakerInfo] = {}
        self._embedding_threshold = getattr(
            settings, "speaker_similarity_threshold", 0.7
        )

        # 加载已有数据
        self._load()

        logger.info(
            "说话人注册系统初始化完成",
            path=str(self._storage_path),
            speakers=len(self._speakers),
        )

    def register_speaker(
        self,
        speaker_id: str,
        name: str,
        embeddings: list[float] | None = None,
        podcast_name: str | None = None,
        role: str = "guest",
    ) -> SpeakerInfo:
        """注册说话人.

        Args:
            speaker_id: 说话人 ID
            name: 说话人名称
            embeddings: 声音特征嵌入向量
            podcast_name: 所属播客
            role: 角色

        Returns:
            注册成功的说话人信息
        """
        # 检查是否已存在
        if speaker_id in self._speakers:
            existing = self._speakers[speaker_id]
            # 更新所有字段
            if embeddings:
                existing.embeddings = embeddings
            if podcast_name is not None:
                existing.podcast_name = podcast_name
            if name:
                existing.name = name
            if role:
                existing.role = role
            logger.info(
                "更新已有说话人信息",
                speaker_id=speaker_id,
                name=existing.name,
            )
            self._save()
            return existing

        # 创建新说话人
        speaker = SpeakerInfo(
            speaker_id=speaker_id,
            name=name,
            embeddings=embeddings,
            podcast_name=podcast_name,
            role=role,
        )
        self._speakers[speaker_id] = speaker

        logger.info(
            "注册新说话人",
            speaker_id=speaker_id,
            name=name,
            podcast=podcast_name,
        )

        self._save()
        return speaker

    def identify_speaker(
        self,
        embeddings: list[float],
        min_confidence: float | None = None,
    ) -> SpeakerInfo | None:
        """通过嵌入向量识别说话人.

        Args:
            embeddings: 待识别的嵌入向量
            min_confidence: 最小置信度阈值

        Returns:
            识别出的说话人信息，或 None
        """
        threshold = min_confidence or self._embedding_threshold

        try:
            import numpy as np

            query_embedding = np.array(embeddings)

            best_match = None
            best_score = 0.0

            for speaker_id, speaker in self._speakers.items():
                if not speaker.embeddings:
                    continue

                ref_embedding = np.array(speaker.embeddings)

                # 计算余弦相似度
                similarity = self._cosine_similarity(query_embedding, ref_embedding)

                if similarity > best_score:
                    best_score = similarity
                    best_match = speaker

            if best_match and best_score >= threshold:
                logger.info(
                    "说话人识别成功",
                    speaker_id=best_match.speaker_id,
                    name=best_match.name,
                    confidence=best_score,
                )
                return best_match
            else:
                logger.debug(
                    "未找到匹配的说话人",
                    best_score=best_score if best_match else "N/A",
                    threshold=threshold,
                )
                return None

        except ImportError:
            logger.warning("numpy 未安装，无法进行说话人识别")
            return None
        except Exception as e:
            logger.warning(f"说话人识别失败: {e}")
            return None

    def get_all_speakers(
        self,
        podcast_name: str | None = None,
        role: str | None = None,
    ) -> list[SpeakerInfo]:
        """获取所有说话人.

        Args:
            podcast_name: 筛选特定播客
            role: 筛选特定角色

        Returns:
            说话人列表
        """
        speakers = list(self._speakers.values())

        if podcast_name:
            speakers = [s for s in speakers if s.podcast_name == podcast_name]

        if role:
            speakers = [s for s in speakers if s.role == role]

        return speakers

    def get_speaker(self, speaker_id: str) -> SpeakerInfo | None:
        """获取指定说话人.

        Args:
            speaker_id: 说话人 ID

        Returns:
            说话人信息或 None
        """
        return self._speakers.get(speaker_id)

    def update_speaker_name(self, speaker_id: str, new_name: str) -> SpeakerInfo | None:
        """更新说话人名称.

        Args:
            speaker_id: 说话人 ID
            new_name: 新名称

        Returns:
            更新后的说话人信息
        """
        speaker = self._speakers.get(speaker_id)
        if not speaker:
            logger.warning(f"说话人不存在: {speaker_id}")
            return None

        old_name = speaker.name
        speaker.name = new_name

        logger.info(
            "更新说话人名称",
            speaker_id=speaker_id,
            old_name=old_name,
            new_name=new_name,
        )

        self._save()
        return speaker

    def remove_speaker(self, speaker_id: str) -> bool:
        """删除说话人.

        Args:
            speaker_id: 说话人 ID

        Returns:
            是否删除成功
        """
        if speaker_id not in self._speakers:
            return False

        del self._speakers[speaker_id]
        logger.info("删除说话人", speaker_id=speaker_id)
        self._save()
        return True

    def export_registry(self, output_path: Path) -> None:
        """导出注册信息.

        Args:
            output_path: 输出文件路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "speakers": {
                sid: info.to_dict() for sid, info in self._speakers.items()
            },
            "total_count": len(self._speakers),
        }
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("说话人注册信息已导出", path=str(output_path))

    def import_registry(self, input_path: Path) -> int:
        """导入注册信息.

        Args:
            input_path: 输入文件路径

        Returns:
            导入的说话人数量
        """
        if not input_path.exists():
            raise SpeakerRegistryError(f"文件不存在: {input_path}")

        data = json.loads(input_path.read_text(encoding="utf-8"))

        count = 0
        for speaker_id, speaker_data in data.get("speakers", {}).items():
            speaker = SpeakerInfo.from_dict(speaker_data)
            self._speakers[speaker_id] = speaker
            count += 1

        self._save()
        logger.info("说话人注册信息已导入", count=count)
        return count

    @staticmethod
    def _cosine_similarity(a: Any, b: Any) -> float:
        """计算余弦相似度.

        Args:
            a: 向量 a
            b: 向量 b

        Returns:
            余弦相似度 (0-1)
        """
        import numpy as np

        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm == 0 or b_norm == 0:
            return 0.0

        return float(np.dot(a, b) / (a_norm * b_norm))

    def _save(self) -> None:
        """保存注册信息到文件."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "speakers": {
                sid: info.to_dict() for sid, info in self._speakers.items()
            }
        }
        self._storage_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self) -> None:
        """从文件加载注册信息."""
        if not self._storage_path.exists():
            return

        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            for speaker_id, speaker_data in data.get("speakers", {}).items():
                self._speakers[speaker_id] = SpeakerInfo.from_dict(speaker_data)
        except Exception as e:
            logger.warning(f"加载说话人注册信息失败: {e}")


class SpeakerMappingManager:
    """说话人标签映射管理器.

    管理自动生成的说话人标签（如 SPEAKER_0）到实际名称的映射。
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """初始化映射管理器.

        Args:
            storage_path: 存储路径
        """
        self._storage_path = storage_path or (
            settings.data_dir / "speakers" / "mappings.json"
        )
        self._mappings: dict[str, str] = {}

        self._load()

    def set_mapping(self, speaker_id: str, name: str) -> None:
        """设置说话人标签映射.

        Args:
            speaker_id: 说话人 ID（如 SPEAKER_0）
            name: 实际名称
        """
        self._mappings[speaker_id] = name
        self._save()
        logger.info("设置说话人映射", speaker_id=speaker_id, name=name)

    def get_mapping(self, speaker_id: str) -> str | None:
        """获取说话人标签映射.

        Args:
            speaker_id: 说话人 ID

        Returns:
            实际名称或 None
        """
        return self._mappings.get(speaker_id)

    def get_all_mappings(self) -> dict[str, str]:
        """获取所有映射.

        Returns:
            映射字典
        """
        return dict(self._mappings)

    def clear_mappings(self) -> None:
        """清除所有映射."""
        self._mappings.clear()
        self._save()
        logger.info("已清除所有说话人映射")

    def _save(self) -> None:
        """保存映射到文件."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(
            json.dumps(self._mappings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self) -> None:
        """从文件加载映射."""
        if not self._storage_path.exists():
            return

        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._mappings = data
        except Exception as e:
            logger.warning(f"加载说话人映射失败: {e}")
