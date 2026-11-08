"""Create and verify one consistent backup; prune only this job's own files."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import time


def maintain(root, retention_days=7):
    root = Path(root).resolve()
    source = root / 'data/miniprogram-server/mini.sqlite3'
    if not source.is_file():
        raise FileNotFoundError('Production database not found; nothing was removed')
    folder = root / 'data/miniprogram-auto-backups'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = folder / f'daily-{stamp}.sqlite3'
    partial = target.with_suffix('.partial')
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30)) as old:
            with closing(sqlite3.connect(partial)) as copy:
                old.backup(copy, pages=128, sleep=0.05)
        # Restore into a distinct disposable database and verify what can be read.
        with tempfile.TemporaryDirectory(prefix='.restore-', dir=folder) as scratch:
            restored = Path(scratch) / 'restored.sqlite3'
            with closing(sqlite3.connect(partial.as_uri() + '?mode=ro', uri=True)) as backup:
                with closing(sqlite3.connect(restored)) as recovery:
                    backup.backup(recovery)
                    if recovery.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Restored database failed integrity check')
                    count = recovery.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        partial.replace(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    cutoff = time.time() - retention_days * 86400
    pruned = 0
    locked_logs = 0
    # Never touch manually created upgrade backups, model caches, or production rows.
    for old in folder.glob('daily-*.sqlite3'):
        if old != target and old.stat().st_mtime < cutoff:
            old.unlink()
            pruned += 1
    logs = root / 'data/managed-api-logs'
    if logs.is_dir():
        for old in logs.glob('managed-api-*.log'):
            if old.stat().st_mtime < cutoff:
                try:
                    old.unlink()
                    pruned += 1
                except PermissionError:
                    # The running server may keep its stderr log open for days.
                    locked_logs += 1
    report = {'status': 'passed', 'backup': str(target), 'restored_integrity': 'ok',
              'restored_task_count': count, 'retention_days': retention_days,
              'pruned_owned_files': pruned, 'locked_logs_skipped': locked_logs,
              'finished_at_utc': datetime.now(timezone.utc).isoformat()}
    (folder / 'latest-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--retention-days', type=int, default=7)
    args = parser.parse_args()
    if args.retention_days < 1:
        parser.error('Retention must be positive')
    print(json.dumps(maintain(args.root, args.retention_days)))
