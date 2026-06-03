"""运行 SenseVoice 转录测试."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from core.transcriber import Transcriber
from config.settings import STTProvider
from models.podcast import PodcastEpisode
from utils import configure_logging

configure_logging('INFO')

# 创建播客单集对象
audio_path = Path('./data/audio/面基_最新单集.wav')
episode = PodcastEpisode(
    title='资产配置与有效前沿',
    audio_url='https://example.com/test.m4a',
    feed_title='面基',
)
episode.local_audio_path = audio_path

# 使用 SenseVoice 转录
print('正在初始化 SenseVoice 转录器...')
transcriber = Transcriber(provider=STTProvider.SENSEVOICE)

print('开始转录...')
transcript = transcriber.transcribe(episode, language='zh')

print(f'\n转录完成！')
print(f'总字数: {transcript.word_count}')
print(f'片段数: {transcript.segment_count}')
print(f'语言: {transcript.language}')
print(f'时长: {transcript.duration_seconds:.0f} 秒')
print()

# 保存完整转录文本
output_path = Path('./data/transcripts/面基_最新单集_transcript.txt')
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f'播客: 面基\n')
    f.write(f'单集: 资产配置与有效前沿\n')
    f.write(f'总字数: {transcript.word_count}\n')
    f.write(f'片段数: {transcript.segment_count}\n')
    f.write(f'时长: {transcript.duration_seconds:.0f} 秒\n')
    f.write('=' * 50 + '\n\n')
    f.write(transcript.full_text)
    f.write('\n\n')
    f.write('=' * 50 + '\n')
    f.write('分段详情:\n')
    for i, seg in enumerate(transcript.segments[:20]):
        f.write(f'\n[{i+1}] [{seg.start_time:.1f}s - {seg.end_time:.1f}s]\n')
        f.write(f'文本: {seg.text}\n')
        if seg.emotion:
            f.write(f'情感: {seg.emotion}\n')
        if seg.audio_event:
            f.write(f'事件: {seg.audio_event}\n')

print(f'转录结果已保存到: {output_path}')

# 打印前 10 个片段
print('\n前 10 个片段预览:')
for seg in transcript.segments[:10]:
    print(f'  [{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.text[:60]}')
    if seg.emotion:
        print(f'    情感: {seg.emotion}')
    if seg.audio_event:
        print(f'    事件: {seg.audio_event}')
