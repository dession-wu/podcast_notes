"""Account gateway and bounded isolated runtimes for the legacy podcast pipeline.

The legacy pipeline has process-global clients and stores. Each account therefore
gets its own runtime and data root; credentials never cross runtime boundaries.
"""
import asyncio
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from starlette.background import BackgroundTask
from backend.web_accounts import router, user, BOX

ROOT=Path('/app/data/users')
ROOT.mkdir(parents=True,exist_ok=True)
workers={}
lock=asyncio.Lock()

async def runtime(current):
    async with lock:
        uid=current['id'];signature=hashlib.sha256(str((current['key'],current['provider'])).encode()).hexdigest()
        worker=workers.get(uid)
        if worker and (worker['process'].poll() is not None or worker['signature']!=signature):
            if worker['active']:raise HTTPException(409,'当前任务进行中，请完成后再修改模型设置。')
            worker['process'].terminate();workers.pop(uid);worker=None
        if worker:
            worker['last']=time.monotonic();worker['active']+=1;return worker
        for other,entry in list(workers.items()):
            if entry['process'].poll() is not None or (not entry['active'] and time.monotonic()-entry['last']>3600):
                if entry['process'].poll() is None:entry['process'].terminate()
                workers.pop(other)
        if len(workers)>=8:raise HTTPException(503,'当前服务器使用人数较多，请稍后再试。')
        folder=ROOT/uid;folder.mkdir(parents=True,exist_ok=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=os.environ.copy()
        for name in list(env):
            if any(part in name.upper() for part in ('API_KEY','API_SECRET','AUTH_TOKEN')):env[name]=''
        # Explicit values also override .env or environment defaults.
        for name in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','ELEVENLABS_API_KEY','PODCASTINDEX_API_KEY','PODCASTINDEX_API_SECRET','LISTENNOTES_API_KEY'):env[name]=''
        token=secrets.token_urlsafe(48)
        env.update(PODCAST_TENANT_WORKER='1',STT_PROVIDER='elevenlabs',DATA_DIR=str(folder),TEMP_DIR=str(folder/'temp'),PODCAST_NOTES_JOBS_DB=str(folder/'jobs.sqlite3'),PODCAST_NOTES_NOTES_DB=str(folder/'notes.sqlite3'),PODCAST_NOTES_API_KEY=token,PODCAST_NOTES_ALLOW_ANONYMOUS='false',DEFAULT_LLM_PROVIDER='openai',OPENAI_BASE_URL='https://api.deepseek.com' if current['provider']=='deepseek' else 'https://api.openai.com/v1',OPENAI_MODEL='deepseek-chat' if current['provider']=='deepseek' else 'gpt-4o-mini',OPENAI_API_KEY=BOX.decrypt(current['key'].encode()).decode() if current['key'] else '',TENANT_CREDENTIAL_FILE='/app/data/accounts/encryption.key')
        env.update(PODCAST_WEB_OWNER=uid,PODCAST_WEB_QUOTA_DIR=str(Path(os.environ.get('ACCOUNT_DATA_DIR','/app/data/accounts'))),PODCAST_WEB_PERSONAL_KEY=BOX.decrypt(current['key'].encode()).decode() if current['key'] else '',PODCAST_WEB_PERSONAL_PROVIDER=current['provider'])
        for name in ('BAILIAN_API_KEY','BAILIAN_API_KEY_FILE'):
            env[name]=os.environ.get(name,'')
        process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.web_worker:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        worker={'process':process,'port':port,'token':token,'last':time.monotonic(),'active':1,'signature':signature}
        workers[uid]=worker
        async with httpx.AsyncClient() as client:
            for _ in range(120):
                if process.poll() is not None:
                    workers.pop(uid,None);raise HTTPException(503,'个人工作空间未能启动，请稍后重试。')
                try:
                    response=await client.get(f'http://127.0.0.1:{port}/api/health/',timeout=1)
                    if response.status_code==200:return worker
                except httpx.HTTPError:pass
                await asyncio.sleep(.25)
        process.terminate();workers.pop(uid,None);raise HTTPException(503,'个人空间启动超时，请重试。')

def create_public_app():
    app=FastAPI(title='Podcast Notes Accounts',docs_url=None,redoc_url=None,openapi_url=None)
    app.include_router(router)

    @app.get('/auth/session')
    def session(request:Request):
        user(request)
        from fastapi import Response
        return Response(status_code=204,headers={'Cache-Control':'no-store'})

    @app.get('/api/health/')
    def health():return {'status':'ok','version':'accounts-1'}

    @app.api_route('/{path:path}',methods=['GET','POST','PUT','DELETE','PATCH','HEAD'])
    async def proxy(path:str,request:Request):
        if not (path.startswith('api/') or path.startswith('images/')):raise HTTPException(404)
        current=user(request)
        if path in ('api/settings/download-path','api/settings/download-path/validate') and request.method!='GET':
            raise HTTPException(403,'在线账号使用自己的默认目录，不支持指定服务器路径。')
        if path=='api/settings/application' and request.method=='PUT':
            values=await request.json()
            if values.get('llm_api_key') or values.get('llm_provider') not in (None,'openai'):
                raise HTTPException(409,'请使用「我的模型」配置 AI 服务商和 Key。')
        worker=await runtime(current)
        client=httpx.AsyncClient(timeout=httpx.Timeout(600,connect=10))
        headers={k:v for k,v in request.headers.items() if k.lower() not in ('host','cookie','authorization','x-api-key','connection','content-length')}
        headers['X-API-Key']=worker['token']
        url=f'http://127.0.0.1:{worker["port"]}/'+path
        if request.url.query:url+='?'+request.url.query
        try:
            content=request.stream()
            # request.json() consumed the body above; replay the cached bytes.
            if path=='api/settings/application' and request.method=='PUT':content=await request.body()
            outbound=client.build_request(request.method,url,headers=headers,content=content)
            response=await client.send(outbound,stream=True)
        except Exception:
            worker['active']-=1;await client.aclose();raise HTTPException(502,'个人空间连接失败，请重试。')
        async def close():
            await response.aclose();await client.aclose();worker['active']-=1;worker['last']=time.monotonic()
        output_headers={k:v for k,v in response.headers.items() if k.lower() not in ('connection','transfer-encoding','content-encoding','content-length')}
        output_headers['Cache-Control']='no-store'
        return StreamingResponse(response.aiter_bytes(),status_code=response.status_code,headers=output_headers,background=BackgroundTask(close))
    return app

