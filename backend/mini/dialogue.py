"""Local Mandarin dialogue transcription with model-derived timing and speakers."""
import math
import re


def parse_sentences(results):
    segments = []
    speakers = {}
    for item in results:
        for sentence in item.get('sentence_info', []):
            text = re.sub(r'<\|[^|]+\|>', '', sentence.get('text', '')).strip()
            if not text:
                continue
            start, end = sentence.get('start'), sentence.get('end')
            if (not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                    or not math.isfinite(start) or not math.isfinite(end)
                    or start < 0 or end <= start):
                raise ValueError('模型未返回有效的句级时间戳，未生成估算时间')
            speaker = None
            raw = sentence.get('spk')
            if raw is not None:
                speaker = speakers.setdefault(str(raw), f'说话人 {len(speakers) + 1}')
            segments.append({'start_time': start / 1000, 'end_time': end / 1000,
                             'text': text, 'speaker': speaker})
    if not segments:
        raise ValueError('模型未返回带时间戳的语句，请检查音频或使用基础转写模式')
    return sorted(segments, key=lambda segment: segment['start_time'])


def format_text(segments):
    lines = []
    for segment in segments:
        seconds = int(segment['start_time'])
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        timestamp = f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'
        speaker = ' ' + segment['speaker'] if segment.get('speaker') else ''
        lines.append(f'[{timestamp}]{speaker}\n{segment["text"]}')
    return '\n\n'.join(lines)


def transcribe_dialogue(audio_path):
    from funasr import AutoModel
    import torch

    # FunASR's VAD + punctuation path supplies sentence_info and speaker assignments.
    model = AutoModel(model='paraformer-zh', vad_model='fsmn-vad',
                      punc_model='ct-punc', spk_model='cam++',
                      device='cuda:0' if torch.cuda.is_available() else 'cpu',
                      disable_update=True)
    results = model.generate(input=str(audio_path), batch_size_s=60,
                             sentence_timestamp=True, return_raw_text=True)
    segments = parse_sentences(results)
    return {'segments': segments, 'text': format_text(segments), 'engine': 'paraformer-zh+cam++'}
