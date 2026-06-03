# STT 智能语言分流系统设计文档

## 1. 设计目标

根据播客音频的语言类型，自动选择最优的 STT (Speech-to-Text) 引擎：
- **中文/粤语/日语/韩语** → SenseVoice (更高的中文准确率 + 情感识别)
- **英文/其他语言** → Whisper (更高的英文准确率 + 更成熟的生态)

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Transcription Request                    │
│                      (音频文件路径)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Language Detector (语言检测器)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  基于文件名  │  │  基于元数据  │  │  音频采样检测 (VAD)  │  │
│  │  规则匹配   │  │  RSS标签    │  │  (10-30秒片段)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   Detected Language │
            │    (zh/en/yue/ja/   │
            │      ko/other)      │
            └──────────┬──────────┘
                       │
         ┌─────────────┼─────────────┐
         │                           │
         ▼                           ▼
┌─────────────────┐      ┌─────────────────┐
│  SenseVoice     │      │  Whisper        │
│  (中文/粤语/    │      │  (英文/其他)    │
│   日语/韩语)    │      │                 │
└────────┬────────┘      └────────┬────────┘
         │                        │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   Unified Transcript   │
         │   (标准化输出格式)      │
         └────────────────────────┘
```

## 3. 核心组件

### 3.1 LanguageDetector (语言检测器)

```python
class LanguageDetector:
    """多层级语言检测器"""
    
    # 检测策略优先级
    PRIORITY = [
        "rss_metadata",      # 1. RSS 源语言标签
        "filename_pattern",  # 2. 文件名模式匹配
        "audio_sample",      # 3. 音频采样检测 (使用轻量级模型)
    ]
    
    # 语言到 STT 引擎的映射
    ENGINE_MAP = {
        "zh": "sensevoice",      # 中文 → SenseVoice
        "yue": "sensevoice",     # 粤语 → SenseVoice
        "ja": "sensevoice",      # 日语 → SenseVoice
        "ko": "sensevoice",      # 韩语 → SenseVoice
        "en": "whisper",         # 英文 → Whisper
        "default": "whisper",    # 其他 → Whisper
    }
```

### 3.2 SmartTranscriber (智能转录器)

```python
class SmartTranscriber:
    """基于语言的智能转录器"""
    
    def transcribe(self, episode: PodcastEpisode) -> Transcript:
        # 1. 检测语言
        language = self.language_detector.detect(episode)
        
        # 2. 选择引擎
        engine = self._select_engine(language)
        
        # 3. 执行转录
        if engine == "sensevoice":
            return self._transcribe_with_sensevoice(episode, language)
        else:
            return self._transcribe_with_whisper(episode, language)
```

## 4. 语言检测策略详解

### 4.1 RSS 元数据检测 (优先级最高)

从播客 RSS 源中的 `<language>` 标签获取：
```xml
<channel>
    <language>zh-CN</language>  <!-- 中文 -->
    <language>en-US</language>  <!-- 英文 -->
</channel>
```

### 4.2 文件名模式匹配

常见播客命名约定：
```python
FILENAME_PATTERNS = {
    r"[\u4e00-\u9fff]+": "zh",           # 包含中文字符
    r"\b(cn|chinese|中文)\b": "zh",       # 中文标识
    r"\b(yue|cantonese|粤语)\b": "yue",   # 粤语标识
    r"\b(jp|japanese|日语)\b": "ja",      # 日语标识
    r"\b(kr|korean|韩语)\b": "ko",        # 韩语标识
    r"\b(en|english|英文)\b": "en",       # 英文标识
}
```

### 4.3 音频采样检测 (兜底策略)

当以上方法都无法确定语言时，提取音频前 10-30 秒，使用轻量级语言检测模型：
- 方案 A: 使用 `langdetect` 库分析转录文本样本
- 方案 B: 使用 `speechbrain/lang-id` 模型直接检测音频

## 5. 配置更新

### 5.1 新增配置项

```python
# config/settings.py

class STTRoutingStrategy(str, Enum):
    """STT 路由策略"""
    AUTO = "auto"           # 自动根据语言选择
    WHISPER_ONLY = "whisper_only"   # 仅使用 Whisper
    SENSEVOICE_ONLY = "sensevoice_only"  # 仅使用 SenseVoice

class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # STT 路由配置
    stt_routing_strategy: STTRoutingStrategy = Field(
        default=STTRoutingStrategy.AUTO,
        description="STT 引擎路由策略",
    )
    
    # 语言检测配置
    language_detection_sample_seconds: int = Field(
        default=15,
        description="语言检测采样时长(秒)",
    )
    
    # SenseVoice 特定配置
    sensevoice_model: str = Field(
        default="iic/SenseVoiceSmall",
        description="SenseVoice 模型路径",
    )
```

### 5.2 依赖更新

```txt
# requirements.txt

# 现有依赖
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# STT 引擎 (根据路由策略按需安装)
# Whisper (英文优化)
openai-whisper>=20231117
faster-whisper>=0.10.0

# SenseVoice (中文优化)
funasr>=1.1.0
modelscope>=1.10.0

# 语言检测
langdetect>=1.0.9
```

## 6. 实现计划

### Phase 1: 基础架构 (已完成调研)
- [x] 调研 SenseVoice vs Whisper 技术差异
- [x] 确认语言准确率差异
- [x] 设计分流系统架构

### Phase 2: 核心实现
- [ ] 实现 LanguageDetector 类
- [ ] 实现 SmartTranscriber 类
- [ ] 更新配置系统
- [ ] 添加依赖管理

### Phase 3: 集成测试
- [ ] 中文播客转录测试
- [ ] 英文播客转录测试
- [ ] 混合语言播客测试
- [ ] 性能基准测试

### Phase 4: 优化迭代
- [ ] 根据测试结果调整检测阈值
- [ ] 优化引擎切换逻辑
- [ ] 添加缓存机制

## 7. 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 中文播客 CER | ~5.3% | ~4.8% |
| 英文播客 WER | ~5.2% | ~4.9% |
| 中文处理速度 | 慢 (Whisper) | 快 (SenseVoice) |
| 情感识别 | ❌ | ✅ (中文) |
| 引擎自动选择 | ❌ | ✅ |

## 8. 风险评估

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| SenseVoice 依赖冲突 | 中 | 高 | 使用独立虚拟环境 |
| 语言检测误判 | 低 | 中 | 多级检测 + 置信度阈值 |
| 内存占用增加 | 中 | 中 | 延迟加载 + 模型缓存 |
| 双语播客处理 | 中 | 低 | 默认使用 Whisper |

---

**文档状态**: 设计完成，等待实现
**更新日期**: 2026-05-28
