"""Exercise actual STT plus Mini API on owned audio with a local download fixture.

Only the network download is substituted; duration probe, subprocess, model,
ownership, storage, export and cleanup use the real implementations.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

project = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(project))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--audio',type=Path,required=True)
parser.add_argument('--mode',choices=['basic','dialogue'],default='basic')
args=parser.parse_args()
audio=args.audio.resolve()
assert audio.is_file()
os.environ['MINI_TRANSCRIPT_MODE']=args.mode
os.environ.setdefault('MODELSCOPE_CACHE',str(project/'data/model-cache/modelscope'))
os.environ.setdefault('HF_HOME',str(project/'data/model-cache/huggingface'))
from fastapi.testclient import TestClient
from backend.mini.app import create_app

start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='mini-pipeline-check-') as temp:
    root=Path(temp)
    app=create_app(root,development=True,demo=False,worker=False)
    with TestClient(app) as client:
        token=client.post('/mini/login',json={'code':'dev:owned-audio-pipeline-validation'}).json()['token']
        headers={'Authorization':'Bearer '+token}
        ep=app.state.store.put('episode',{'title':'中文语音识别自制样例','feed_title':'自制测试音频','audio_url':'https://example.invalid/owned-sample.wav'})
        created=client.post('/mini/tasks',headers=headers,json={'episode_id':ep,'rights_confirmed':True})
        assert created.status_code==202
        key=created.json()['id']
        def owned_download(url,limit,target):
            assert url=='https://example.invalid/owned-sample.wav'
            assert audio.stat().st_size<=limit
            shutil.copyfile(audio,target)
        with patch('backend.mini.app.fetch',side_effect=owned_download):
            app.state.process(app.state.store.claim())
        result=client.get('/mini/tasks/'+key,headers=headers).json()
        assert result['status']=='completed',result.get('error')
        timing=result['timing']
        assert timing['mode']==args.mode and timing['elapsed_seconds'] >= timing['processing_seconds'] >= 0
        assert '文字' in result['text'] and '语音' in result['text']
        if args.mode == 'dialogue':
            assert result['segments'] and all(s['end_time'] > s['start_time'] >= 0 for s in result['segments'])
            assert any(s.get('speaker') for s in result['segments'])
        exported=client.get('/mini/tasks/'+key+'/export',headers=headers)
        assert exported.status_code==200 and exported.text=='\ufeff'+result['text']
        assert not list(root.glob('*.audio')) and not list(root.glob('*.work'))
        assert client.delete('/mini/tasks/'+key,headers=headers).status_code==204
        assert client.get('/mini/tasks/'+key,headers=headers).status_code==404
report={'status':'passed','audio':'owned synthesized Chinese sample','mode':args.mode,'timing':timing,'download_transport':'local fixture (public network download not covered)','real_components':['ffprobe','STT subprocess','Paraformer/CAM++' if args.mode == 'dialogue' else 'SenseVoice','user task storage','authenticated TXT export','delete','temporary file cleanup'],'elapsed_seconds':round(time.monotonic()-start,2)}
out=project/'data/miniprogram-model-check/pipeline-validation.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
