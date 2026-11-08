"""Make a consistent local SQLite backup before upgrading the mini API."""
from datetime import datetime
from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parents[1]
source = root / 'data/miniprogram-server/mini.sqlite3'
if not source.is_file():
    raise SystemExit('Database not found; no files changed.')
folder = root / 'data/miniprogram-backups'
folder.mkdir(parents=True, exist_ok=True)
target = folder / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
with sqlite3.connect(source) as old, sqlite3.connect(target) as backup:
    old.backup(backup)
print('Backup saved: ' + str(target))
