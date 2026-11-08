"""Temporary tunnel connectivity probe. Exposes no files, login or podcast data.

Run on the target Windows computer: python windows_tunnel_probe.py
Then tunnel ONLY http://127.0.0.1:18010. Stop with Ctrl+C.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Probe(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/tunnel-check':
            self.send_error(404)
            return
        body = json.dumps({'service': 'podnotes-tunnel-probe', 'probe_only': True,
                           'backend_ready': False}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    server = HTTPServer(('127.0.0.1', 18010), Probe)
    print('Connectivity probe: http://127.0.0.1:18010/tunnel-check')
    print('This is NOT the podcast backend. Ctrl+C stops the probe.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
