"""Mini API regression tests; no external services or transcription costs."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.parse import urlsplit
import socket
import sqlite3
import hashlib
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.mini.app import create_app
from backend.mini.network import destination, fetch
from backend.mini.store import Store

@pytest.fixture
def service(tmp_path):
    app = create_app(tmp_path, development=True, demo=True, worker=False)
    with TestClient(app) as client:
        yield app, client

def auth(client, identity='alice'):
    result = client.post('/mini/login', json={'code': 'dev:' + identity * 12})
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['token']}

def episode(client, headers):
    feed = client.get('/mini/search?q=test', headers=headers).json()['results'][0]
    return client.get('/mini/feeds/' + feed['id'] + '/episodes', headers=headers).json()['episodes'][0]['id']

def submit(client, headers, ep):
    return client.post('/mini/tasks', headers=headers, json={'episode_id':ep, 'rights_confirmed':True})

def test_health_identifies_actual_database_without_exposing_path(service):
    app, client = service
    health = client.get('/mini/health').json()
    path = str(Path(app.state.store.path).resolve())
    expected = hashlib.sha256(os.path.normcase(path).encode()).hexdigest()[:16]
    assert health['storage_id'] == expected
    assert health['runtime_diagnostics_version'] == 4
    assert health['worker_protocol'] == 4
    assert path not in str(health)

def test_legacy_connection_cannot_take_task_after_protocol_upgrade(tmp_path):
    path = tmp_path / 'mini.sqlite3'
    # An already-open connection must also obey a newly installed trigger.
    with sqlite3.connect(path) as legacy:
        store = Store(path)
        job = store.admit('owner', 'episode', 'Keep this task')
        with pytest.raises(sqlite3.IntegrityError, match='Legacy mini worker'):
            legacy.execute("UPDATE jobs SET status='downloading' WHERE id=?", (job['id'],))
        legacy.rollback()
        assert store.job(job['id'], 'owner')['status'] == 'queued'
        Store(path)  # Repeated startup preserves the guard and data.
        claimed = store.claim()
        assert claimed['id'] == job['id']
        assert claimed['status'] == 'downloading'
        assert claimed['claim_version'] == 4
        assert claimed['claim_pid'] == os.getpid()
        assert store.claim() is None

def test_protocol_claim_is_atomic_between_new_workers(tmp_path):
    store = Store(tmp_path/'mini.sqlite3')
    job = store.admit('owner', 'episode', 'Only once')
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(lambda _: store.claim(), range(6)))
    assert [row['id'] for row in claims if row] == [job['id']]

def test_worker_health_reflects_running_thread(tmp_path):
    app = create_app(tmp_path, development=True, demo=True)
    with TestClient(app) as client:
        assert client.get('/mini/health').json()['worker_alive'] is True
    assert app.state.worker_thread.is_alive() is False

def test_complete_flow_ownership_and_delete(service):
    app, client = service
    a,b = auth(client),auth(client,'bob')
    assert client.get('/mini/session',headers=a).json()['demo'] is True
    assert client.get('/mini/session').status_code == 401
    ep = episode(client,a)
    result = submit(client,a,ep)
    assert result.status_code == 202
    job = result.json()
    assert submit(client,a,ep).json()['id'] == job['id']
    assert client.get('/mini/tasks/'+job['id']+'/export',headers=a).status_code == 409
    for suffix in ('','/export'):
        assert client.get('/mini/tasks/'+job['id']+suffix,headers=b).status_code == 404
    assert client.delete('/mini/tasks/'+job['id'],headers=b).status_code == 404
    assert client.delete('/mini/tasks/'+job['id'],headers=a).status_code == 409
    app.state.process(app.state.store.claim())
    text = client.get('/mini/tasks/'+job['id'],headers=a).json()['text']
    assert '演示内容' in text
    exported = client.get('/mini/tasks/'+job['id']+'/export',headers=a)
    assert exported.status_code == 200 and exported.text == '\ufeff'+text
    assert client.get('/mini/tasks',headers=b).json() == {'tasks':[]}
    assert client.delete('/mini/tasks/'+job['id'],headers=a).status_code == 204
    assert client.get('/mini/tasks/'+job['id'],headers=a).status_code == 404
    assert client.get('/mini/tasks',headers=a).json() == {'tasks':[]}

def test_auth_validation_and_expiry(service):
    app,client = service
    assert client.get('/mini/tasks').status_code == 401
    assert client.get('/mini/tasks',headers={'Authorization':'Bearer bogus'}).status_code == 401
    assert client.post('/mini/login',json={'code':'spoof'}).status_code == 400
    headers=auth(client)
    assert client.post('/mini/tasks',headers=headers,json={'episode_id':'unknown'}).status_code == 422
    assert submit(client,headers,'unknown').status_code == 404
    assert client.get('/mini/search?q=',headers=headers).status_code == 422
    with app.state.store.db() as db:
        db.execute('UPDATE sessions SET expires=0')
    assert client.get('/mini/tasks',headers=headers).status_code == 401

def test_atomic_admission_and_quota(tmp_path):
    store=Store(tmp_path/'test.sqlite3')
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(lambda _:store.admit('a','ep','title'),range(6)))
    assert len({r['id'] for r in rows}) == 1
    with pytest.raises(ValueError,match='已有任务'):
        store.admit('a','different','title')
    store.update(rows[0]['id'],'completed',text='private')
    store.delete(rows[0]['id'],'a')
    for _ in range(2):
        row=store.admit('a','ep','title');store.update(row['id'],'failed')
    with pytest.raises(ValueError,match='额度'):
        store.admit('a','ep','title')

def test_recovery_and_queue_persistence(tmp_path):
    path=tmp_path/'test.sqlite3';store=Store(path)
    first=store.admit('a','one','title');second=store.admit('b','two','title')
    with store.db() as db:
        db.execute('UPDATE jobs SET created=1 WHERE id=?',(first['id'],))
        db.execute('UPDATE jobs SET created=2 WHERE id=?',(second['id'],))
    store.claim();other=Store(path);other.recover()
    assert other.job(first['id'],'a')['status']=='failed'
    assert other.claim()['id']==second['id']
    assert other.job(first['id'],'b') is None

def test_production_configuration(tmp_path,monkeypatch):
    with pytest.raises(RuntimeError):
        create_app(tmp_path,development=False,demo=True)
    monkeypatch.delenv('WECHAT_APP_SECRET',raising=False)
    with TestClient(create_app(tmp_path,development=False,demo=False,worker=False)) as client:
        assert client.post('/mini/login',json={'code':'dev:'+'x'*40}).status_code==503
        assert client.get('/openapi.json').status_code==404

def test_wechat_exchange(tmp_path,monkeypatch):
    monkeypatch.setenv('WECHAT_APP_ID','test-id');monkeypatch.setenv('WECHAT_APP_SECRET','test-secret')
    class FakeClient:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,url,params):
            assert params['grant_type']=='authorization_code'
            class Result:
                def raise_for_status(self): pass
                def json(self): return {'openid':'private-id','session_key':'never-return'}
            return Result()
    with patch('backend.mini.app.httpx.AsyncClient',FakeClient):
        with TestClient(create_app(tmp_path,development=False,demo=False,worker=False)) as client:
            result=client.post('/mini/login',json={'code':'wechat-code'})
            assert result.status_code==200
            assert 'openid' not in result.text and 'session_key' not in result.text
            assert client.get('/mini/tasks',headers={'Authorization':'Bearer '+result.json()['token']}).status_code==200

@pytest.mark.parametrize('url',['file:///etc/passwd','http://user:pass@example.com','http://example.com:8080','http://example.com/#test'])
def test_invalid_url(url):
    with pytest.raises(ValueError): destination(url)

@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','169.254.169.254','::1','::ffff:127.0.0.1'])
def test_private_dns(ip):
    with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,80))]):
        with pytest.raises(ValueError,match='公网'): destination('https://example.com/feed')

def test_public_dns():
    with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]):
        assert destination('https://example.com/feed')[2]=='8.8.8.8'

def test_rate_limit(service):
    _,client=service
    for _ in range(20):
        assert client.post('/mini/login',json={'code':'dev:'+'a'*30}).status_code==200
    assert client.post('/mini/login',json={'code':'dev:'+'a'*30}).status_code==429

def test_size_and_redirect_checks():
    class Sock:
        def close(self): pass
    class Reply:
        status=200
        def getheader(self,name): return '99999' if name=='Content-Length' else None
    class Conn:
        def __init__(self,*args,**kwargs): pass
        def request(self,*args,**kwargs): pass
        def getresponse(self): return Reply()
        def close(self): pass
    parsed=urlsplit('http://example.com')
    with patch('backend.mini.network.destination',return_value=(parsed,80,'8.8.8.8')),patch('http.client.HTTPConnection',Conn),patch('socket.create_connection',return_value=Sock()):
        with pytest.raises(ValueError,match='大小限制'): fetch('http://example.com',10)
    Reply.status=302
    Reply.getheader=lambda self,name:'http://127.0.0.1/private' if name=='Location' else None
    with patch('backend.mini.network.destination',side_effect=[(parsed,80,'8.8.8.8'),ValueError('公网')]) as resolve,patch('http.client.HTTPConnection',Conn),patch('socket.create_connection',return_value=Sock()):
        with pytest.raises(ValueError,match='公网'): fetch('http://example.com',10)
        assert resolve.call_count==2

def test_real_rss_adapter_and_bounded_local_worker(tmp_path):
    app=create_app(tmp_path,development=True,demo=False,worker=False)
    feed_id=app.state.store.put('feed',{'title':'Authorized Test','rss_url':'https://example.com/rss'})
    rss=b'''<rss version="2.0"><channel><title>Test</title><item><title>Episode A</title><enclosure url="https://example.com/a.mp3" type="audio/mpeg" length="100" /></item></channel></rss>'''
    with TestClient(app) as client:
        headers=auth(client)
        with patch('backend.mini.app.fetch',return_value=rss):
            result=client.get('/mini/feeds/'+feed_id+'/episodes',headers=headers)
        assert result.status_code==200
        ep=result.json()['episodes'][0]['id']
        job=submit(client,headers,ep).json()
        def run(args,**kwargs):
            if args[0]=='ffprobe':
                return type('Probe',(),{'stdout':'12.5'})()
            assert kwargs['timeout']==7200
            assert kwargs['env']['DATA_DIR'].endswith('.work')
            from pathlib import Path
            Path(args[-1]).write_text('A mocked local model result',encoding='utf-8')
        with patch('backend.mini.app.fetch',return_value=b'audio'),patch('backend.mini.app.subprocess.run',side_effect=run):
            app.state.process(app.state.store.claim())
        assert client.get('/mini/tasks/'+job['id'],headers=headers).json()['text']=='A mocked local model result'
        assert not list(tmp_path.glob('*.work')) and not list(tmp_path.glob('*.json'))


def test_actual_worker_thread_completes_demo(tmp_path):
    import time
    with TestClient(create_app(tmp_path,development=True,demo=True,worker=True)) as client:
        headers=auth(client);ep=episode(client,headers)
        job=submit(client,headers,ep).json()
        for _ in range(30):
            result=client.get('/mini/tasks/'+job['id'],headers=headers).json()
            if result['status']=='completed': break
            time.sleep(.05)
        assert result['status']=='completed'
