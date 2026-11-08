"""Account-only ASGI operation boundary, including GET generation and threadpool calls."""
import hashlib, json, os, secrets, tempfile
from fastapi import HTTPException
from backend.web_llm import SCOPE,ledger
from backend.main import app as original_app

class Worker:
    def __init__(self, app):
        self.app=app
        ledger().recover()
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        with tempfile.SpooledTemporaryFile(max_size=1024*1024) as body:
            return await self.http(scope,receive,send,body)
    async def http(self,scope,receive,send,body):
        owner=os.environ.get('PODCAST_WEB_OWNER','')
        digest=hashlib.sha256()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            chunk=message.get('body',b'')
            body.write(chunk);digest.update(chunk)
            if not message.get('more_body'):break
        body_size=body.tell()
        body.seek(0)
        headers=dict(scope.get('headers',[]))
        operation=headers.get(b'x-llm-operation-id',b'').decode('ascii','ignore') or secrets.token_hex(20)
        if len(operation)>128:
            return await self.error(send,400,'操作编号过长')
        fingerprint=hashlib.sha256(json.dumps([scope['method'],scope['path'],scope.get('query_string',b'').hex(),digest.hexdigest()]).encode()).hexdigest()
        with ledger().connect() as c:
            prior=c.execute('SELECT fingerprint,state,response FROM operations WHERE owner=? AND id=?',(owner,operation)).fetchone()
        if prior:
            if prior[0]!=fingerprint:return await self.error(send,409,'操作编号与请求不匹配')
            if prior[1]=='reserved':return await self.error(send,409,'操作正在处理中')
            if prior[1]=='succeeded':
                if not prior[2]:return await self.error(send,409,'操作已生成有效结果，请查看已保存结果')
                saved=json.loads(prior[2])
                await send({'type':'http.response.start','status':saved['status'],'headers':[(a.encode('latin1'),b.encode('latin1')) for a,b in saved['headers']]})
                return await send({'type':'http.response.body','body':bytes.fromhex(saved['body'])})
        state={'owner':owner,'id':operation,'fingerprint':fingerprint}
        token=SCOPE.set(state)
        used=False
        async def replay():
            nonlocal used
            if not used:
                chunk=body.read(65536)
                used=body.tell()>=body_size
                return {'type':'http.request','body':chunk,'more_body':not used}
            return await receive()
        output=[]
        async def capture(message):
            if state.get('reserved') or state.get('error'):output.append(message)
            else:await send(message)
        try:
            await self.app(scope,replay,capture)
            if state.get('replay'):
                saved=json.loads(state['replay'])
                await send({'type':'http.response.start','status':saved['status'],'headers':[(a.encode('latin1'),b.encode('latin1')) for a,b in saved['headers']]})
                return await send({'type':'http.response.body','body':bytes.fromhex(saved['body'])})
            if state.get('error'):
                if state.get('reserved'):ledger().finish(owner,operation,bool(state.get('valid')))
                return await self.error(send,*state['error'])
            if state.get('reserved'):
                start=next(m for m in output if m['type']=='http.response.start')
                data=b''.join(m.get('body',b'') for m in output if m['type']=='http.response.body')
                saved=json.dumps({'status':start['status'],'headers':[(a.decode('latin1'),b.decode('latin1')) for a,b in start['headers']],'body':data.hex()})
                # A valid model result already commits the trial even if a later step fails.
                ledger().finish(owner,operation,bool(state.get('valid')),saved if state.get('valid') else None)
                if state.get('valid'):
                    with ledger().connect() as c:c.execute('UPDATE operations SET response=? WHERE owner=? AND id=?',(saved,owner,operation))
            for message in output:await send(message)
        except HTTPException as exc:
            if state.get('reserved'):ledger().finish(owner,operation,bool(state.get('valid')))
            await self.error(send,exc.status_code,exc.detail)
        except BaseException:
            if state.get('reserved'):ledger().finish(owner,operation,bool(state.get('valid')))
            raise
        finally:SCOPE.reset(token)
    async def error(self,send,status,detail):
        await send({'type':'http.response.start','status':status,'headers':[(b'content-type',b'application/json')]})
        await send({'type':'http.response.body','body':json.dumps({'detail':detail},ensure_ascii=False).encode()})
app=Worker(original_app)
