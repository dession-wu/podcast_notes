"""Compile native templates/styles with the installed official WeChat compilers.

No login, network access, code upload or IDE setting changes. Outputs stay temporary.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', default='/Applications/wechatwebdevtools.app')
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent / 'miniprogram'
    executables = Path(args.app) / 'Contents/Resources/app.asar.unpacked/node_modules/wcc-exec'
    if not all((executables / name).is_file() for name in ('wcc', 'wcsc')):
        parser.error('Install official WeChat DevTools or pass its .app path with --app')
    pages = json.loads((project / 'app.json').read_text(encoding='utf-8'))['pages']
    templates = [page + '.wxml' for page in pages]
    styles = ['app.wxss'] + [page + '.wxss' for page in pages if (project / (page + '.wxss')).exists()]
    with tempfile.TemporaryDirectory(prefix='podcast-mini-compile-') as output:
        for compiler, files, target in [('wcc', templates, 'wxml.js'), ('wcsc', styles, 'wxss.js')]:
            result = subprocess.run([str(executables / compiler), '-o', str(Path(output) / target), *files],
                                    cwd=project, text=True, capture_output=True)
            if result.returncode:
                print(result.stderr or result.stdout)
                raise SystemExit(result.returncode)
            if not (Path(output) / target).stat().st_size:
                raise SystemExit(f'{compiler} returned empty output')
            print(f'{compiler}: PASS ({len(files)} source files)')
    print('Official compiler checks passed. Simulator and device testing are separate steps.')


if __name__ == '__main__':
    main()
