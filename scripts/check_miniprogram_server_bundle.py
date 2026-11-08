"""Check packaged imports and real-mode RSS parsing in an isolated extracted bundle."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='podnotes-bundle-') as folder:
    with zipfile.ZipFile(root / 'deploy/miniprogram/podnotes-windows-server.zip') as archive:
        names = archive.namelist()
        assert 'podnotes-server/backend/config/download_settings.py' in names
        assert all(Path(name).suffix in ('.py', '.txt') for name in names)
        archive.extractall(folder)
    project = Path(folder) / 'podnotes-server'
    code = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from unittest.mock import patch
from fastapi.testclient import TestClient
from core.audio_downloader import AudioDownloader
from backend.mini.transcribe_worker import SmartTranscriber
from backend.mini.dialogue import parse_sentences, format_text
assert '[00:01]' in format_text(parse_sentences([{'sentence_info':[{'start':1000,'end':2000,'text':'Bundle timing','spk':0}]}]))
from backend.mini.app import create_app
rss=b'<?xml version="1.0"?><rss version="2.0"><channel><title>Bundle fixture</title><item><title>Episode one</title><guid>bundle-fixture</guid><enclosure url="https://example.com/audio.mp3" type="audio/mpeg" length="123"/></item></channel></rss>'
app=create_app('test-data',development=True,demo=False,worker=False)
feed=app.state.store.put('feed',{'title':'Bundle fixture','rss_url':'https://example.com/feed.xml'})
with TestClient(app) as client:
    token=client.post('/mini/login',json={'code':'dev:'+'bundle-fixture'*3}).json()['token']
    with patch('backend.mini.app.fetch',return_value=rss):
        response=client.get('/mini/feeds/'+feed+'/episodes',headers={'Authorization':'Bearer '+token})
    assert response.status_code==200, response.status_code
    assert response.json()['episodes'][0]['title']=='Episode one'
print('PASS isolated bundle imports and non-demo RSS endpoint (mocked feed transport)')
'''
    result = subprocess.run([sys.executable, '-I', '-c', code], cwd=project,
                            env={**os.environ, 'DATA_DIR': str(project / 'test-data'), 'TEMP_DIR': str(project / 'test-temp')},
                            capture_output=True, text=True, timeout=45)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
