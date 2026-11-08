"""Project-local atomic operations. No credential values are persisted here."""
import os, sqlite3, hashlib, json
from pathlib import Path
from contextvars import ContextVar
from contextlib import contextmanager
from fastapi import HTTPException
SCOPE=ContextVar('llm_operation',default=None)
ENDPOINTS={'bailian':('https://dashscope.aliyuncs.com/compatible-mode/v1','qwen3.7-flash'),'deepseek':('https://api.deepseek.com','deepseek-chat'),'openai':('https://api.openai.com/v1','gpt-4o-mini')}

def operator_key():
    key=os.environ.get('BAILIAN_API_KEY','').strip()
    if key:return key
    name=os.environ.get('BAILIAN_API_KEY_FILE')
    if not name and os.name=='nt':
        default=Path(r'E:\podnotes\podnotes-server\config\ops-secrets\bailian-secret.bin')
        if default.is_file():name=str(default)
    if not name:return None
    if os.name!='nt':raise HTTPException(503,'DPAPI 文件仅支持 Windows；容器请注入 BAILIAN_API_KEY')
    import ctypes
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    raw=Path(name).read_bytes();buf=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw);src=Blob(len(raw),buf);out=Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src),None,None,None,None,0,ctypes.byref(out)):
        raise HTTPException(503,'运营模型密钥无法解密')
    try:return ctypes.string_at(out.pbData,out.cbData).decode().strip()
    finally:ctypes.windll.kernel32.LocalFree(out.pbData)

class Ledger:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS operations(owner TEXT,id TEXT,fingerprint TEXT,state TEXT,pid INTEGER,response TEXT,source TEXT NOT NULL DEFAULT 'platform', PRIMARY KEY(owner,id))")
            if 'source' not in [row[1] for row in c.execute('PRAGMA table_info(operations)')]:
                try:c.execute("ALTER TABLE operations ADD COLUMN source TEXT NOT NULL DEFAULT 'platform'")
                except sqlite3.OperationalError as error:
                    if 'duplicate column' not in str(error):raise
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            with c:yield c
        finally:c.close()
    def recover(self):
        # Never release live workers simply because a second worker starts.
        with self.connect() as c:
            for pid, in c.execute("SELECT DISTINCT pid FROM operations WHERE state='reserved'"):
                if os.name=='nt':
                    import ctypes
                    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                    kernel.OpenProcess.restype=ctypes.c_void_p
                    handle=kernel.OpenProcess(0x1000,False,pid)
                    if handle:
                        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
                        kernel.CloseHandle(handle)
                    elif ctypes.get_last_error()==87:
                        c.execute("UPDATE operations SET state='failed' WHERE state='reserved' AND pid=?",(pid,))
                    continue
                try:os.kill(pid,0)
                except ProcessLookupError:c.execute("UPDATE operations SET state='failed' WHERE state='reserved' AND pid=?",(pid,))
                except (PermissionError,OSError):pass
    def status(self,owner):
        with self.connect() as c:
            used=c.execute("SELECT count(*) FROM operations WHERE owner=? AND source='platform' AND state='succeeded'",(str(owner),)).fetchone()[0]
            pending=c.execute("SELECT count(*) FROM operations WHERE owner=? AND source='platform' AND state='reserved'",(str(owner),)).fetchone()[0]
        return {'used':used,'reserved':pending,'remaining':max(0,3-used-pending),'model':'qwen3.7-flash'}
    def reserve(self,owner,operation,fingerprint,source="platform"):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT fingerprint,state,response FROM operations WHERE owner=? AND id=?',(str(owner),operation)).fetchone()
            if old:
                if old[0]!=fingerprint:raise HTTPException(409,'操作编号与请求不匹配')
                if old[1]=='succeeded':
                    if old[2] is None:raise HTTPException(409,'操作已生成有效结果，请查看已保存结果')
                    return old[2]
                if old[1]=='reserved':raise HTTPException(409,'操作正在处理中')
            count=c.execute("SELECT count(*) FROM operations WHERE owner=? AND source='platform' AND state IN ('reserved','succeeded')",(str(owner),)).fetchone()[0]
            if source=='platform' and count>=3:raise HTTPException(409,{'code':'quota_exhausted','message':'三次免费体验已用尽，请配置自己的百炼 API Key。'})
            c.execute('INSERT OR REPLACE INTO operations(owner,id,fingerprint,state,pid,response,source) VALUES(?,?,?,?,?,NULL,?)',(str(owner),operation,fingerprint,'reserved',os.getpid(),source))
        return None
    def finish(self,owner,operation,success,response=None):
        with self.connect() as c:c.execute("UPDATE operations SET state=?,response=? WHERE owner=? AND id=? AND state='reserved'",('succeeded' if success else 'failed',response,str(owner),operation))

# One gateway-authenticated user per isolated runtime; never accept owner headers.
def ledger():
    return Ledger(Path(os.environ.get('PODCAST_WEB_QUOTA_DIR', os.environ.get('ACCOUNT_DATA_DIR','/app/data/accounts'))) / 'web_llm.sqlite3')

def credentials():
    scope=SCOPE.get()
    if not scope or not scope.get('owner'):
        raise HTTPException(401,'AI 操作缺少账号身份')
    if scope.get('credentials'):return scope['credentials']
    personal=os.environ.get('PODCAST_WEB_PERSONAL_KEY','')
    provider=os.environ.get('PODCAST_WEB_PERSONAL_PROVIDER','bailian')
    try:
        if personal:
            replay=ledger().reserve(scope['owner'],scope['id'],scope['fingerprint'],'personal')
            if replay is not None:
                scope['replay']=replay
                raise HTTPException(409,'操作已完成')
            scope['reserved']=True
            scope['credentials']=(provider,personal)
            return scope['credentials']
        key=operator_key()
        if not key:raise HTTPException(503,'运营模型未配置，请在 /account 配置个人 Key')
        replay=ledger().reserve(scope['owner'],scope['id'],scope['fingerprint'])
        if replay is not None:
            scope['replay']=replay
            raise HTTPException(409,'操作已完成')
        scope['reserved']=True
        scope['credentials']=('bailian',key)
        return scope['credentials']
    except HTTPException as error:
        scope['error']=(error.status_code,error.detail)
        raise
