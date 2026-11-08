"""Read recent task metadata locally; never prints secrets or transcript contents."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import os
import subprocess
import urllib.request
from zoneinfo import ZoneInfo


def describe_process(row, root):
    """Only allowlisted metadata leaves this function; never return command lines."""
    command = row.get('CommandLine') or ''
    normalized = command.lower().replace('\\', '/')
    roles = [label for needle, label in (
        ('run_miniprogram_server.py', 'mini server launcher'),
        ('backend.mini.app', 'mini API'),
        ('backend.mini.transcribe_worker', 'transcription worker'),
        ('uvicorn', 'uvicorn API'),
        ('run_miniprogram_local.py', 'local mini launcher'),
    ) if needle in normalized]
    if not roles:
        roles = ['unclassified Python process']
    mode = re.search(r'--mode\s+(basic|dialogue)\b', command)
    port = re.search(r'--port\s+(\d+)\b', command)
    return {'pid': row.get('ProcessId'), 'parent_pid': row.get('ParentProcessId'),
            'executable': row.get('ExecutablePath'), 'started': row.get('CreationDate'),
            'roles': roles, 'explicit_mode': mode.group(1) if mode else None,
            'explicit_port': int(port.group(1)) if port else None,
            'references_this_project': str(root).lower().replace('\\', '/') in normalized}


def inspect_runtime(root):
    result = {}
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8010/mini/health', timeout=5) as response:
            health = json.load(response)
        result['local_health'] = {k: health[k] for k in (
            'status', 'development', 'demo', 'transcript_mode', 'transcript_format_version',
            'runtime_diagnostics_version', 'storage_id', 'worker_protocol', 'worker_alive') if k in health}
    except Exception as error:
        result['local_health_error'] = type(error).__name__
    if os.name == 'nt':
        try:
            # Capture locally, then discard command lines rather than printing them.
            query = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python.*|uvicorn)(\\.exe)?$' } | Select-Object ProcessId,ParentProcessId,ExecutablePath,CreationDate,CommandLine | ConvertTo-Json -Compress"
            output = subprocess.run(['powershell.exe', '-NoProfile', '-Command', query],
                                    capture_output=True, text=True, timeout=20, check=True)
            rows = json.loads(output.stdout) if output.stdout.strip() else []
            if isinstance(rows, dict):
                rows = [rows]
            result['mini_processes'] = [item for row in rows if (item := describe_process(row, root))]
            ports = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                'Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=20)
            result['listeners_8010'] = json.loads(ports.stdout) if ports.stdout.strip() else []
        except Exception as error:
            result['process_check_error'] = type(error).__name__
    return result


def inspect_database(path, limit=5):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        columns = {row['name'] for row in db.execute('PRAGMA table_info(jobs)')}
        rows = db.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT ?', (limit,)).fetchall()
        results = []
        for row in rows:
            text = row['text'] or ''
            segments = json.loads(row['segments']) if 'segments' in columns else []
            timing = json.loads(row['timing']) if 'timing' in columns else {}
            results.append({
                'id': row['id'], 'title': row['title'], 'status': row['status'],
                'created_local': datetime.fromtimestamp(row['created'], ZoneInfo('Asia/Shanghai')).isoformat(),
                'segment_count': len(segments),
                'speakers': sorted({s['speaker'] for s in segments if s.get('speaker')}),
                'first_start': segments[0].get('start_time') if segments else None,
                'last_end': segments[-1].get('end_time') if segments else None,
                'text_length': len(text), 'legacy_header': text.startswith('Title:'),
                'text_timestamp_count': len(re.findall(r'\[\d{2}:\d{2}(?::\d{2})?\]', text)),
                'timing': timing,
                'claim_version': row['claim_version'] if 'claim_version' in columns else None,
                'claim_pid': row['claim_pid'] if 'claim_pid' in columns else None,
            })
    return results


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=root/'data/miniprogram-server/mini.sqlite3')
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error('Database does not exist; no files were changed')
    versions = {}
    for name in ('backend/mini/app.py', 'backend/mini/store.py', 'backend/mini/dialogue.py', 'backend/mini/transcribe_worker.py', 'scripts/run_miniprogram_server.py'):
        versions[name] = hashlib.sha256((root/name).read_bytes()).hexdigest()
    runtime = inspect_runtime(root)
    storage_id = hashlib.sha256(os.path.normcase(str(args.db.resolve())).encode()).hexdigest()[:16]
    running_id = runtime.get('local_health', {}).get('storage_id')
    print(json.dumps({'diagnostic_version': 4, 'source_sha256': versions, 'runtime': runtime,
                      'database_matches_running_service': running_id == storage_id if running_id else None,
                      'database': str(args.db.resolve()),
                      'recent_tasks': inspect_database(args.db)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
