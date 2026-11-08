"""Check the scheduled-task identity's model and database access without secrets."""
import json
from pathlib import Path
import shutil
import sqlite3
import os
import torch
import funasr

root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'config/managed-runtime.json').read_text(encoding='utf-8-sig'))
os.environ['PATH'] = config['ffmpeg_directory'] + os.pathsep + os.environ['PATH']
with sqlite3.connect((root / 'data/miniprogram-server/mini.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
    integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
report = {'cuda': torch.cuda.is_available(), 'database_integrity': integrity,
          'funasr_import': True, 'ffmpeg_available': shutil.which('ffmpeg') is not None}
(root / 'data/managed-api-logs/system-preflight.json').write_text(json.dumps(report), encoding='utf-8')
if not report['cuda'] or integrity != 'ok' or not report['ffmpeg_available']:
    raise SystemExit(1)
