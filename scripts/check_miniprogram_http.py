"""Smoke check a running LOCAL DEMO server, no real audio/API calls."""
import json
import time
from urllib.request import Request, urlopen

base = 'http://127.0.0.1:8010/mini'

def call(path, token='', data=None):
    req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                  headers={'Content-Type':'application/json', **({'Authorization':'Bearer '+token} if token else {})})
    with urlopen(req, timeout=10) as response:
        return json.load(response)

health = call('/health')
assert health['demo'] and health['development'], 'Only run this test against a local demo service'
session = call('/login', data={'code':'dev:http-smoke-check-unique-identity'})
token = session['token']
feed = call('/search?q=demo', token)['results'][0]
episode = call('/feeds/'+feed['id']+'/episodes', token)['episodes'][0]
job = call('/tasks', token, {'episode_id':episode['id'],'rights_confirmed':True})
for _ in range(20):
    result = call('/tasks/'+job['id'], token)
    if result['status'] in ('completed','failed'):
        break
    time.sleep(.25)
assert result['status'] == 'completed', result['status']
assert '演示内容' in result['text']
with urlopen(Request(base+'/tasks/'+job['id']+'/export', headers={'Authorization':'Bearer '+token}),timeout=10) as res:
    assert '演示内容' in res.read().decode('utf-8-sig')
print('HTTP demo smoke passed: login -> search -> episodes -> persistent worker -> transcript -> TXT')
