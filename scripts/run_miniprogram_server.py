"""Start the real mini-program API on the target computer; one worker only."""
import argparse
import getpass
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['basic', 'dialogue'],
                        default=os.getenv('MINI_TRANSCRIPT_MODE', 'dialogue'))
    parser.add_argument('--daily-limit', type=int, default=int(os.getenv('MINI_DAILY_LIMIT', '3')))
    args = parser.parse_args()
    if args.daily_limit < 1:
        parser.error('--daily-limit must be positive')
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10 or newer is required; Python 3.12 recommended.')
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    sys.path.insert(0, str(root))
    try:
        import uvicorn
    except ImportError:
        raise SystemExit('Install backend/requirements.txt in the dedicated environment first.')
    os.environ['MINI_DEVELOPMENT'] = 'false'
    os.environ['MINI_DEMO'] = 'false'
    os.environ['WECHAT_APP_ID'] = 'wxcf1571f64e71f165'
    os.environ['MINI_TRANSCRIPT_MODE'] = args.mode
    os.environ['MINI_DAILY_LIMIT'] = str(args.daily_limit)
    secret = os.environ.get('WECHAT_APP_SECRET') or getpass.getpass('WeChat AppSecret (hidden; do not share): ')
    if not secret.strip():
        raise SystemExit('AppSecret is required. Server not started.')
    secret = secret.strip()
    if any(ord(char) < 33 or ord(char) > 126 for char in secret):
        raise SystemExit('AppSecret input contains whitespace, control or non-ASCII characters. Use PowerShell Read-Host -AsSecureString to enter it; no request was sent.')
    os.environ['WECHAT_APP_SECRET'] = secret
    os.environ.setdefault('MINI_DATA_DIR', str(root / 'data' / 'miniprogram-server'))
    os.environ.setdefault('MODELSCOPE_CACHE', str(root / 'data' / 'model-cache' / 'modelscope'))
    os.environ.setdefault('HF_HOME', str(root / 'data' / 'model-cache' / 'huggingface'))
    print('Starting API on 127.0.0.1:8010. Keep this window open.')
    print(f'Transcript mode: {args.mode}; daily limit: {args.daily_limit}.')
    print('Database: ' + str((Path(os.environ['MINI_DATA_DIR']) / 'mini.sqlite3').resolve()))
    print('Python environment: ' + sys.prefix)
    print('Model dependencies, ffmpeg and actual transcription require separate verification.')
    uvicorn.run('backend.mini.app:create_app', factory=True, host='127.0.0.1',
                port=8010, workers=1, proxy_headers=False)


if __name__ == '__main__':
    main()
