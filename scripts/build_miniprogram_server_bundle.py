"""Build the credential-free Windows server bundle from an explicit source allowlist."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parents[1]
files = set()
for folder in ('backend/mini', 'backend/config', 'config', 'core', 'models', 'services', 'utils'):
    files.update(p for p in (root / folder).rglob('*.py') if '__pycache__' not in p.parts)
for name in ('backend/__init__.py', 'backend/requirements.txt', 'scripts/run_miniprogram_server.py', 'scripts/check_miniprogram_public.py',
             'scripts/check_miniprogram_transcription.py', 'scripts/check_miniprogram_transcription_pipeline.py',
             'scripts/backup_miniprogram_store.py'):
    files.add(root / name)
output = root / 'deploy/miniprogram/podnotes-windows-server.zip'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for source in sorted(files):
        archive.write(source, 'podnotes-server/' + source.relative_to(root).as_posix())
    archive.writestr('podnotes-server/START_HERE.txt',
        'Use Python 3.12 and install backend/requirements.txt.\n'
        'Start: python scripts/run_miniprogram_server.py\n'
        'AppSecret must be provided locally; never send it in chat.\n'
        'Windows: prefer PowerShell secure input or clipboard over getpass Ctrl+V.\n'
        'API listens only on 127.0.0.1:8010; keep the terminal open.\n'
        'Models and ffmpeg are not bundled; verify transcription separately.\n'
        'Launcher defaults to dialogue when MINI_TRANSCRIPT_MODE is unset; use --mode dialogue explicitly.\n'
        'Use scripts/backup_miniprogram_store.py before upgrading an existing database.\n'
        'This archive contains no credentials, environment files, databases or model weights.\n')
print(f'{output.name}: {len(files)} source files, {output.stat().st_size} bytes')
print('SHA256 ' + hashlib.sha256(output.read_bytes()).hexdigest())

patch = output.with_name('podnotes-windows-config-fix.zip')
with zipfile.ZipFile(patch, 'w', zipfile.ZIP_DEFLATED) as archive:
    for source in sorted((root / 'backend/config').glob('*.py')):
        archive.write(source, source.relative_to(root).as_posix())
print(f'{patch.name}: {patch.stat().st_size} bytes; extract into the existing podnotes-server directory')

dialogue = output.with_name('podnotes-windows-dialogue-update.zip')
with zipfile.ZipFile(dialogue, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ('backend/mini/dialogue.py', 'backend/mini/app.py', 'backend/mini/store.py',
                 'backend/mini/transcribe_worker.py', 'scripts/run_miniprogram_server.py', 'scripts/check_miniprogram_transcription.py',
                 'scripts/check_miniprogram_transcription_pipeline.py', 'scripts/backup_miniprogram_store.py'):
        archive.write(root / name, name)
    archive.write(root / 'docs/miniprogram/DIALOGUE_TRANSCRIPTION.md', 'DIALOGUE_TRANSCRIPTION.md')
print(f'{dialogue.name}: {dialogue.stat().st_size} bytes; existing data and credentials excluded')

mode_fix = output.with_name('podnotes-windows-mode-timing-fix.zip')
mode_fix.write_bytes(dialogue.read_bytes())
print(f'{mode_fix.name}: {mode_fix.stat().st_size} bytes')
