"""Read-only HTTPS health check; never sends credentials or switches client config."""
import argparse
import json
import sys
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--origin', default='https://api.podnotes.cloud')
args = parser.parse_args()
from urllib.parse import urlsplit
origin = urlsplit(args.origin)
if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.query or origin.fragment or origin.path not in ('', '/'):
    parser.error('origin must be a plain HTTPS origin without credentials, path, query or fragment')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

url = args.origin.rstrip('/') + '/mini/health'
try:
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': 'Podnotes-Deployment-Check/1.0', 'Accept': 'application/json'})
    with opener.open(request, timeout=12) as response:
        body = response.read(65537)
        if len(body) > 65536:
            raise ValueError('health response exceeds 64KB')
        data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError('health response must be a JSON object')
    checks = {'https_health': True, 'development_disabled': data.get('development') is False,
              'demo_disabled': data.get('demo') is False}
    print(json.dumps({'url': url, 'checks': checks}, ensure_ascii=False, indent=2))
    print('Does not verify ICP filing, WeChat domain settings, login or transcription.')
    sys.exit(0 if all(checks.values()) else 1)
except (OSError, ValueError, urllib.error.URLError) as exc:
    print(f'BLOCK {url}: {exc}', file=sys.stderr)
    sys.exit(1)
