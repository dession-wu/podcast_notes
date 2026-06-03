# 说话人识别系统优化方案

**方案版本**：V1.0  
**撰写日期**：2026-05-30  
**方案状态**：待评审

---

## 一、现状分析

### 1.1 当前系统架构

当前播客笔记系统包含以下语音处理模块：

```
音频输入 → 语言检测 → STT引擎(Whisper/SenseVoice/faster-whisper) → 文本转录 → 内容理解 → 笔记生成
```

### 1.2 说话人识别现状

#### 已实现部分

| 组件 | 状态 | 说明 |
|-----|------|------|
| 数据模型 | ✅ 已完成 | [TranscriptSegment](file:///d:\podcast_notes\models\transcript.py#L11-L28) 包含 `speaker` 字段（可选） |
| 前端展示 | ✅ 已完成 | TranscriptContent.tsx 支持说话人彩色标签显示 |
| 模型预留 | ⚠️ 未使用 | 所有引擎接口中 `speaker` 字段始终为 `None` |

#### 未实现部分

| 组件 | 状态 | 说明 |
|-----|------|------|
| 说话人分离（Diarization） | ❌ 缺失 | 无任何引擎启用说话人识别功能 |
| 说话人嵌入提取 | ❌ 缺失 | 未使用 pyannote 等说话人嵌入模型 |
| 说话人聚类 | ❌ 缺失 | 无说话人身份聚类算法 |
| 说话人标签映射 | ❌ 缺失 | 无说话人 ID 到名称的映射机制 |

### 1.3 核心问题诊断

经过代码分析，当前说话人识别准确率不足的**根本原因**是：

**说话人识别功能完全未实现，而非准确率问题。**

具体问题列表：

| 问题编号 | 问题描述 | 影响程度 |
|---------|---------|---------|
| P1 | Whisper/SenseVoice 转录时未启用 `diarization` 参数 | 🔴 致命 |
| P2 | 转录结果解析器未提取说话人信息 | 🔴 致命 |
| P3 | 未引入专业的说话人分离模型（pyannote/speechbrain） |  致命 |
| P4 | 无说话人聚类与身份一致性管理 |  严重 |
| P5 | 播客场景特有的多人对话处理缺失 | 🟠 严重 |
| P6 | 噪声环境下的说话人特征鲁棒性不足 | 🟡 中等 |
| P7 | 无说话人识别质量评估与可视化反馈 | 🟡 中等 |

---

## 二、问题根因分析

### 2.1 模型架构限制

#### 问题：当前 STT 引擎的说话人识别能力不足

**Whisper 原生限制**：
- Whisper 模型本身**不支持**说话人分离（diarization）
- 官方 Whisper 仅做语音转文字，不输出说话人标签
- 即使启用 `word_timestamps=True`，也只能获取时间戳，无说话人信息

**faster-whisper 限制**：
- faster-whisper 的 `transcribe()` 方法支持 `diarization=True` 参数，但需要额外安装 `pyannote.audio` 依赖
- 当前代码中未传递此参数，也未安装相关依赖

**SenseVoice 限制**：
- SenseVoice 模型本身不具备说话人识别能力
- 仅支持语言检测、情感识别、音频事件检测
- 无说话人分离接口

### 2.2 特征提取方法问题

#### 问题：缺乏专业的说话人特征提取

当前系统无任何说话人特征提取机制：

```
音频波形 → STT 引擎 → 文本 + 时间戳（无说话人信息）
              ↓
         缺失：x-vector / ECAPA-TDNN 说话人嵌入提取
```

**应补充的说话人特征提取方法**：

| 特征类型 | 模型 | 用途 | 优先级 |
|---------|------|------|-------|
| x-vector | ECAPA-TDNN | 说话人嵌入向量提取 | P0 |
| d-vector | d-vector DNN | 轻量级说话人嵌入 | P1 |
| 语音指纹 | SpeechBrain | 说话人识别与验证 | P1 |

### 2.3 训练数据质量与数量

#### 问题：无说话人聚类所需的参考数据

当前系统没有：
- 说话人参考语音库（用于说话人身份注册与识别）
- 说话人标签标注数据（用于监督学习）
- 说话人聚类历史数据（用于增量聚类）

**播客场景特有的数据挑战**：
- 同一期播客中，同一说话人可能在多个不连续的时间段出现
- 不同期播客之间，同一说话人的声学特征可能因录音设备/环境而变化
- 播客通常有 2-4 位固定主持人 + 不固定嘉宾

### 2.4 环境噪声影响

#### 问题：播客音频存在多种噪声干扰

| 噪声类型 | 来源 | 影响 |
|---------|------|------|
| 背景噪声 | 录音环境噪声 | 降低说话人特征提取准确率 |
| 交叉对话 | 多人同时说话 | 导致说话人分离失败 |
| 笑声/掌声 | 现场反应 | 被误识别为说话人 |
| 音乐间隔 | 片头片尾音乐 | 产生假阳性说话人段 |
| 回声/混响 | 远程录制 | 改变说话人声学特征 |

### 2.5 说话人特征差异

#### 播客场景的特殊挑战

| 差异维度 | 说明 | 影响 |
|---------|------|------|
| 音色相似度 | 同性别/同年龄段主持人音色接近 | 聚类混淆 |
| 说话风格 | 同一人不同情绪/语速下特征变化 | 过度分割 |
| 录音设备 | 不同期使用不同麦克风 | 特征漂移 |
| 远程连线 | 电话/网络通话音质 | 特征失真 |

---

## 三、优化方案

### 3.1 优化目标

| 指标 | 当前状态 | 目标值 | 评估方法 |
|-----|---------|-------|---------|
| 说话人识别准确率（DER） | 0%（未实现） | DER ≤ 15% | pyannote.metrics DER 计算 |
| 说话人数量检测准确率 | N/A | ≥ 90% | 人工标注 vs 自动检测对比 |
| 说话人标签一致性 | N/A | ≥ 95% | 同一说话人跨时间段标签一致率 |
| 端到端处理时间增量 | N/A | ≤ 原转录时间的 20% | 基准测试 |
| 交叉对话处理能力 | N/A | 可识别 2 人同时说话场景 | 合成测试音频 |

### 3.2 技术架构设计

#### 优化后的系统架构

```
音频输入
    │
    ├──▶ 语音活动检测（VAD）── 过滤静音段
    │
    ├──▶ 语音转文字（STT）── 文本 + 时间戳
    │
    └──▶ 说话人分离（Diarization）── 说话人标签 + 时间戳
            │
            ├──▶ 说话人嵌入提取（ECAPA-TDNN）
            ├──▶ 说话人聚类（Agglomerative Clustering）
            └──▶ 说话人标签映射（SPEAKER_0 → 主持人名称）
                    │
                    ▼
            结果合并 ───▶ 带说话人标签的转录文本
```

### 3.3 实施方案

#### 阶段一：基础说话人分离（P0）

**目标**：实现基础的说话人分离功能，使 `TranscriptSegment.speaker` 字段能够被正确填充。

**实施步骤**：

##### Step 1: 集成 pyannote.audio 说话人分离引擎

```
新增依赖：
- pyannote.audio >= 2.1.1
- speechbrain >= 0.5.0

新增文件：
- core/speaker_diarizer.py  # 说话人分离核心模块
```

**核心功能设计**：

```python
class SpeakerDiarizer:
    """说话人分离器"""
    
    def __init__(self, config: DiarizerConfig):
        # 加载预训练模型
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )
        
    def diarize(self, audio_path: Path) -> DiarizationResult:
        """对音频进行说话人分离"""
        # 1. VAD 预处理
        # 2. 说话人嵌入提取
        # 3. 聚类
        # 4. 标签输出
```

##### Step 2: 扩展 STT 引擎支持说话人参数

修改 [transcriber.py](file:///d:\podcast_notes\core\transcriber.py#L152-L211) 中的 `_transcribe_with_faster_whisper` 方法：

```python
# 修改前
segments, info = self._faster_whisper_model.transcribe(
    str(audio_path),
    language=language,
    beam_size=5,
    vad_filter=True,
)

# 修改后
segments, info = self._faster_whisper_model.transcribe(
    str(audio_path),
    language=language,
    beam_size=5,
    vad_filter=True,
    diarization=True,  # 启用说话人分离
    word_timestamps=True,  # 启用词级时间戳（用于精确对齐）
)
```

##### Step 3: 修改结果解析器填充说话人字段

修改 [transcriber.py](file:///d:\podcast_notes\core\transcriber.py#L414-L449) 中的 `_parse_faster_whisper_result` 方法：

```python
def _parse_faster_whisper_result(self, segments, info):
    for seg in segments:
        transcript_segments.append(
            TranscriptSegment(
                start_time=seg.start,
                end_time=seg.end,
                text=seg.text.strip(),
                speaker=seg.speaker,  # ← 新增：填充说话人标签
                confidence=seg.avg_logprob,
            )
        )
```

同样修改 [TranscriptSegment](file:///d:\podcast_notes\models\transcript.py#L11-L28) 的保存和展示逻辑以支持说话人标签输出。

##### Step 4: 实现 STT 结果与 Diarization 结果的对齐

当使用 Whisper（不支持原生 diarization）时，需要将 pyannote 的说话人分离结果与 Whisper 的转录结果进行时间轴对齐：

```python
class AlignmentEngine:
    """STT 文本与说话人标签对齐引擎"""
    
    def align(self, transcript: Transcript, diarization: DiarizationResult):
        """将说话人标签映射到转录片段"""
        for segment in transcript.segments:
            # 找到与该片段重叠最多的说话人段
            matching_speaker = self._find_best_match(
                segment.start_time, 
                segment.end_time, 
                diarization
            )
            segment.speaker = matching_speaker
```

##### Step 5: 添加配置项

在 [settings.py](file:///d:\podcast_notes\config\settings.py#L100-L133) 中添加说话人分离相关配置：

```python
# STT 配置扩展
enable_speaker_diarization: bool = Field(
    default=False,
    description="是否启用说话人分离功能",
)

diarization_model: str = Field(
    default="pyannote/speaker-diarization-3.1",
    description="说话人分离模型名称",
)

max_speakers: int | None = Field(
    default=None,
    description="最大说话人数（None 为自动检测）",
)

hf_token: str | None = Field(
    default=None,
    description="HuggingFace API Token（用于下载 pyannote 模型）",
)
```

#### 阶段二：播客场景优化（P1）

**目标**：针对播客场景特点进行专项优化。

##### Step 1: 说话人数量先验知识

利用播客元数据（播客介绍、往期记录）预估说话人数量：

```python
class PodcastSpeakerEstimator:
    """播客说话人数量预估器"""
    
    def estimate(self, podcast_info: PodcastInfo) -> SpeakerCountEstimate:
        """基于播客信息预估说话人数量"""
        # 1. 从播客描述中提取主持人信息
        # 2. 查询往期说话的说话人数量
        # 3. 返回预估值和置信度
```

##### Step 2: 固定主持人识别

实现"主持人注册"功能，建立说话人特征数据库：

```python
class SpeakerRegistry:
    """说话人注册与管理"""
    
    def register_speaker(self, name: str, audio_clip: Path):
        """注册说话人声音特征"""
        embedding = self._extract_embedding(audio_clip)
        self.db[name] = embedding
    
    def identify(self, embedding: np.ndarray) -> str | None:
        """通过声音特征识别说话人"""
        best_match = cosine_similarity(embedding, self.db)
        return best_match if best_match.score > self.threshold else None
```

##### Step 3: 交叉对话处理

优化同时说话场景的处理：

```python
class OverlapHandler:
    """交叉对话处理器"""
    
    def handle_overlap(self, segments: list[Segment]) -> list[Segment]:
        """处理重叠说话段"""
        for seg in segments:
            if seg.num_speakers > 1:
                # 分离重叠段为多个子段
                seg.sub_segments = self._split_overlap(seg)
```

#### 阶段三：噪声鲁棒性增强（P2）

**目标**：提升复杂环境下的说话人识别准确率。

##### Step 1: 音频预处理增强

```python
class AudioPreprocessor:
    """音频预处理增强器"""
    
    def preprocess(self, audio_path: Path) -> Path:
        """预处理音频文件"""
        return (
            self
            ._remove_silence()     # 去除静音段
            ._reduce_noise()       # 降噪处理
            ._normalize_volume()   # 音量归一化
            ._detect_music()       # 检测并标记音乐段
            .output()
        )
```

##### Step 2: VAD（语音活动检测）优化

优化 VAD 参数，减少假阳性和假阴性：

```python
vad_filter=True,
vad_parameters={
    "min_silence_duration_ms": 500,   # 最小静音间隔
    "speech_pad_ms": 100,             # 语音段填充
    "threshold": 0.5,                 # 激活阈值
}
```

##### Step 3: 说话人嵌入质量过滤

```python
class EmbeddingQualityFilter:
    """说话人嵌入质量过滤器"""
    
    def filter(self, embeddings: list[Embedding]) -> list[Embedding]:
        """过滤低质量说话人嵌入"""
        quality_scores = [self._compute_quality(e) for e in embeddings]
        return [e for e, q in zip(embeddings, quality_scores) if q > self.threshold]
```

#### 阶段四：用户体验优化（P2）

**目标**：提供说话人识别质量的可视化反馈和手动修正能力。

##### Step 1: 说话人识别质量指标展示

在 Web 后台展示说话人识别质量：

```typescript
interface DiarizationQuality {
  der: number;          // 说话人错误率
  speaker_count: number; // 检测到的说话人数量
  confidence_scores: Record<string, number>; // 各说话人置信度
  overlap_ratio: number; // 交叉对话比例
}
```

##### Step 2: 说话人标签手动修正

允许用户手动修正说话人标签：

```typescript
// TranscriptContent.tsx 增强
function SpeakerLabel({ segment, onEdit }: Props) {
  return (
    <span className="speaker-label">
      {segment.speaker}
      <button onClick={() => onEdit(segment)}>✏️ 修正</button>
    </span>
  );
}
```

##### Step 3: 说话人名称自定义

允许用户将 `SPEAKER_0`、`SPEAKER_1` 映射为实际名称：

```typescript
interface SpeakerMapping {
  [speakerId: string]: string; // { "SPEAKER_0": "张三", "SPEAKER_1": "李四" }
}
```

### 3.4 评估与验证

#### 评估数据集

| 数据集 | 用途 | 来源 |
|-------|------|------|
| 自建播客测试集 | 核心评估 | 标注 10 期不同风格播客（含 2-5 说话人） |
| AMI 会议语料 | 交叉对话评估 | 公开会议语料库 |
| DIHARD 数据集 | 噪声鲁棒性评估 | 公开噪声语料库 |

#### 评估指标

| 指标 | 公式 | 目标值 |
|-----|------|-------|
| DER（说话人错误率） | (FA + MISS + CF) / Total | ≤ 15% |
| JER（联合错误率） | (FA + MISS + CONF) / Total | ≤ 20% |
| 说话人数量准确率 | |≥ 检测数与真实数一致的比例 | ≥ 90% |
| 标签一致性 | 同一说话人跨时间段标签一致率 | ≥ 95% |

#### 验证流程

```
1. 准备标注数据集（人工标注说话人时间边界）
        ↓
2. 运行优化后的说话人分离系统
        ↓
3. 使用 pyannote.metrics 计算 DER/JER
        ↓
4. 人工抽检 10% 样本，验证说话人标签准确性
        ↓
5. 对比优化前后指标，输出评估报告
```

---

## 四、实施计划

### 4.1 里程碑规划

| 里程碑 | 内容 | 预计时间 | 交付物 |
|-------|------|---------|-------|
| M1 | 阶段一完成：基础说话人分离 | TBD | 可工作的说话人分离模块 + 配置系统 |
| M2 | 阶段二完成：播客场景优化 | TBD | 主持人注册系统 + 交叉对话处理 |
| M3 | 阶段三完成：噪声鲁棒性增强 | TBD | 音频预处理模块 + VAD 优化 |
| M4 | 阶段四完成：用户体验优化 | TBD | 说话人标签修正 UI + 质量展示 |

### 4.2 技术依赖

| 依赖项 | 说明 | 获取方式 |
|-------|------|---------|
| HuggingFace Token | 下载 pyannote 预训练模型 | 注册 huggingface.co 获取 |
| pyannote.audio | 说话人分离核心库 | `pip install pyannote.audio` |
| speechbrain | 说话人嵌入提取 | `pip install speechbrain` |
| GPU（推荐） | 加速模型推理 | NVIDIA GPU + CUDA |

### 4.3 风险与应对

| 风险 | 影响 | 应对措施 |
|-----|------|---------|
| pyannote 模型下载失败 | 无法运行 | 提供离线模型加载方案 |
| GPU 内存不足 | 推理速度慢/崩溃 | 提供 CPU 回退方案 + 分块处理 |
| 说话人聚类参数调优困难 | 准确率不达标 | 提供参数网格搜索工具 |
| 跨期播客说话人识别不一致 | 用户体验差 | 实现说话人注册与特征数据库 |

---

## 五、总结

当前播客笔记系统的"说话人识别准确率不足"问题，本质上是**说话人识别功能完全未实现**的问题。优化方案分为四个阶段：

1. **基础实现**（P0）：集成 pyannote.audio，实现说话人分离与 STT 结果对齐
2. **场景优化**（P1）：针对播客场景优化说话人数量预估、主持人识别和交叉对话处理
3. **鲁棒性增强**（P2）：优化音频预处理、VAD 和说话人嵌入质量过滤
4. **体验优化**（P2）：提供说话人标签手动修正和质量可视化

预期优化后，说话人错误率（DER）可控制在 **15%** 以内，满足播客场景的使用需求。

---

*本方案由技术团队编写，将随实施进展持续更新。*
*最后更新：2026-05-30*
