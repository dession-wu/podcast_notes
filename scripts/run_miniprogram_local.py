"""Local-only mini API. Demo is the default; --real enables actual RSS/local STT."""
import argparse
import os
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
parser = argparse.ArgumentParser()
parser.add_argument('--real', action='store_true')
parser.add_argument('--port', type=int, default=8010)
args = parser.parse_args()
os.environ['MINI_DEVELOPMENT'] = 'true'
os.environ['MINI_DEMO'] = 'false' if args.real else 'true'
os.environ.setdefault('MINI_DATA_DIR', 'data/miniprogram-real' if args.real else 'data/miniprogram-demo')
os.environ.setdefault('MODELSCOPE_CACHE', str(project_root / 'data/miniprogram-model-cache/modelscope'))
os.environ.setdefault('HF_HOME', str(project_root / 'data/miniprogram-model-cache/huggingface'))
import uvicorn
uvicorn.run('backend.mini.app:create_app', factory=True, host='127.0.0.1', port=args.port, workers=1, proxy_headers=False)
