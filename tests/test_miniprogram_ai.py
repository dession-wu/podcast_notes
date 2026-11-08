import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.mini.app import create_app


@pytest.fixture
def service(tmp_path,monkeypatch):
    monkeypatch.setenv('BAILIAN_API_KEY','synthetic-platform-test-only')
    app=create_app(tmp_path,development=True,demo=True,worker=False)
    ai=app.state.ai
    ai.pool.shutdown(wait=False)
    class Queue:
        def submit(self,*args): pass
        def shutdown(self,**kwargs): pass
    ai.pool=Queue()
    monkeypatch.setattr(ai,'invoke',lambda *a,**kw: True if kw.get('validate') else {'condensed_text':'精简结果。','summary':'摘要。','key_points':['观点。']})
    with TestClient(app) as client:
        yield app,client


def job(app,owner,index):
    store=app.state.store
    episode=store.put('episode',{'title':'episode '+str(index)})
    row=store.admit(owner,episode,'Title '+str(index),daily=30)
    store.update(row['id'],'completed',text='这是一段用于测试的播客正文。'*20)
    return row['id']


def headers(app,owner):
    return {'Authorization':'Bearer '+app.state.store.session(owner)}


def finish(app,key,owner):
    state=app.state.ai.get(key,owner)
    app.state.ai.process(state['id'],'正文。','synthetic','https://example.invalid')


def test_lifetime_three_shared_idempotency_and_cache(service):
    app,client=service;auth=headers(app,'a')
    for n in range(3):
        key=job(app,'a',n)
        first=client.post('/mini/tasks/'+key+'/ai',headers=auth).json()
        again=client.post('/mini/tasks/'+key+'/ai',headers=auth).json()
        assert first['id']==again['id']
        finish(app,key,'a')
        cached=client.post('/mini/tasks/'+key+'/ai',headers=auth).json()
        assert cached['status']=='completed' and cached['id']==first['id']
    settings=client.get('/mini/ai/settings',headers=auth).json()
    assert settings['trial_used']==3 and settings['trial_remaining']==0
    key=job(app,'a',4)
    assert client.post('/mini/tasks/'+key+'/ai',headers=auth).status_code==402
    assert app.state.ai.settings('b')['trial_remaining']==3


def test_failure_and_restart_release_only_reserved_operations(service,monkeypatch):
    app,client=service;ai=app.state.ai;key=job(app,'a',1)
    state=ai.submit(key,'a')
    assert ai.settings('a')['trial_reserved']==1
    monkeypatch.setattr(ai,'invoke',lambda *a,**kw: (_ for _ in ()).throw(ValueError('模拟服务失败')))
    ai.process(state['id'],'正文','synthetic','https://example.invalid')
    assert ai.get(key,'a')['status']=='failed' and ai.settings('a')['trial_remaining']==3
    ai.submit(key,'a')
    ai.recover()
    assert ai.get(key,'a')['status']=='queued'  # A second app cannot release live work.
    with app.state.store.db() as db:
        db.execute('UPDATE ai_operations SET pid=0')
    ai.recover()
    assert ai.get(key,'a')['status']=='failed' and ai.settings('a')['trial_remaining']==3


def test_personal_key_is_encrypted_private_and_does_not_reset_quota(service):
    app,client=service;a=headers(app,'a');b=headers(app,'b')
    key=job(app,'a',1);app.state.ai.submit(key,'a');finish(app,key,'a')
    response=client.put('/mini/ai/settings',headers=a,json={'api_key':'synthetic-personal-key','region':'beijing'})
    assert response.status_code==200 and response.json()['personal_configured']
    assert 'synthetic-personal-key' not in response.text
    assert not client.get('/mini/ai/settings',headers=b).json()['personal_configured']
    with app.state.store.db() as db:
        cipher=db.execute('SELECT cipher FROM ai_keys').fetchone()[0]
        assert 'synthetic-personal-key' not in cipher
    other=job(app,'a',2);app.state.ai.submit(other,'a');finish(app,other,'a')
    assert app.state.ai.get(other,'a')['source']=='personal'
    assert app.state.ai.settings('a')['trial_used']==1
    client.delete('/mini/ai/settings',headers=a)
    assert app.state.ai.settings('a')['trial_used']==1
    for method in ('get','post'):
        assert getattr(client,method)('/mini/tasks/'+key+'/ai',headers=b).status_code==404
        assert getattr(client,method)('/mini/tasks/'+key+'/ai').status_code==401


def test_concurrent_reservations_and_unknown_endpoints_are_rejected(service):
    app,client=service;keys=[job(app,'a',i) for i in range(4)]
    def reserve(key):
        from fastapi import HTTPException
        try:return app.state.ai.submit(key,'a')['status']
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(reserve,keys))
    assert responses.count('queued')==1
    assert app.state.ai.settings('a')['trial_reserved']==1
    a=headers(app,'a')
    assert client.put('/mini/ai/settings',headers=a,json={'api_key':'synthetic-key','region':'http://127.0.0.1'}).status_code==422


def test_delete_hides_ai_content_but_preserves_used_quota(service):
    app,client=service;a=headers(app,'a');key=job(app,'a',1)
    app.state.ai.submit(key,'a');finish(app,key,'a')
    assert client.delete('/mini/tasks/'+key,headers=a).status_code==204
    assert client.get('/mini/tasks/'+key+'/ai',headers=a).status_code==404
    assert app.state.ai.settings('a')['trial_used']==1
    with app.state.store.db() as db:
        assert db.execute('SELECT result FROM ai_operations').fetchone()[0]==''


def test_delete_during_ai_cannot_restore_content_or_consume_trial(service,monkeypatch):
    app,client=service;auth=headers(app,'a');key=job(app,'a',1)
    operation=app.state.ai.submit(key,'a')
    def result(*args,**kwargs):
        assert client.delete('/mini/tasks/'+key,headers=auth).status_code==204
        return {'condensed_text':'must not persist','summary':'summary','key_points':['point']}
    monkeypatch.setattr(app.state.ai,'invoke',result)
    app.state.ai.process(operation['id'],'text','synthetic','https://example.invalid')
    with app.state.store.db() as db:
        row=db.execute('SELECT status,result FROM ai_operations').fetchone()
        assert row['status']=='failed' and row['result']==''
    assert app.state.ai.settings('a')['trial_remaining']==3
