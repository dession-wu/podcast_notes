"""Run actual local STT on an owned audio sample; downloads model weights if absent.

No paid provider is used. This check is separate from the demo simulator test.
"""
import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

project = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--audio', type=Path, required=True)
parser.add_argument('--expected', action='append', default=[])
parser.add_argument('--mode', choices=['basic', 'dialogue'], default='basic')
args = parser.parse_args()
audio = args.audio.resolve()
if not audio.is_file():
    parser.error('Audio sample does not exist')
output_dir = project / 'data/miniprogram-model-check'
output_dir.mkdir(parents=True, exist_ok=True)
cache = project / 'data/model-cache'
cache.mkdir(parents=True, exist_ok=True)
probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio)], capture_output=True, text=True, check=True)
duration = float(probe.stdout.strip())
assert duration > 0
report = {'status':'started', 'duration_seconds':duration, 'engine':'Paraformer/CAM++' if args.mode == 'dialogue' else 'SmartTranscriber/local SenseVoice', 'expected':args.expected}
start = time.monotonic()
with tempfile.TemporaryDirectory(prefix='mini-stt-check-') as temp:
    work = Path(temp)
    spec, result = work / 'episode.json', work / 'result.txt'
    spec.write_text(json.dumps({'title':'中文语音识别自制样例', 'feed_title':'自制测试音频', 'audio_url':'', 'local_audio_path':str(audio)},ensure_ascii=False),encoding='utf-8')
    env = {**os.environ, 'DATA_DIR':str(work), 'TEMP_DIR':str(work),
           'ENABLE_SPEAKER_DIARIZATION':'false', 'MINI_TRANSCRIPT_MODE':args.mode,
           'MODELSCOPE_CACHE':str(cache / 'modelscope'), 'HF_HOME':str(cache / 'huggingface')}
    with (output_dir / 'worker.log').open('w',encoding='utf-8') as log:
        process = subprocess.run([sys.executable, '-m', 'backend.mini.transcribe_worker', str(spec), str(result)], cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=7200)
    report['elapsed_seconds'] = round(time.monotonic() - start,2)
    if process.returncode or not result.exists():
        report.update(status='failed', error='See data/miniprogram-model-check/worker.log')
    else:
        text=result.read_text(encoding='utf-8')
        (output_dir / 'transcript.txt').write_text(text,encoding='utf-8')
        missing=[word for word in args.expected if word not in text]
        report.update(status='passed' if text.strip() and not missing else 'failed', missing_keywords=missing, text_length=len(text))
        if args.mode == 'dialogue':
            structured=json.loads(result.with_suffix('.segments.json').read_text(encoding='utf-8'))
            segments=structured['segments']
            assert segments and all(s['end_time'] > s['start_time'] >= 0 for s in segments)
            (output_dir/'transcript-segments.json').write_text(json.dumps(structured,ensure_ascii=False,indent=2),encoding='utf-8')
            report.update(segment_count=len(segments),speaker_count=len({s['speaker'] for s in segments if s.get('speaker')}))
for package in ('funasr','torch','torchaudio'):
    try: report.setdefault('packages',{})[package]=metadata.version(package)
    except metadata.PackageNotFoundError: pass
(output_dir / 'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['status']=='passed' else 1)
