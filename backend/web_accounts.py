"""Independent accounts, private keys and revocable sessions for Podcast Notes."""
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import parse_qs
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

DATA = Path(os.environ.get('ACCOUNT_DATA_DIR', '/app/data/accounts'))
DATA.mkdir(parents=True, exist_ok=True)
KEY = DATA / 'encryption.key'
if not KEY.exists():
    with KEY.open('xb') as stream:
        stream.write(Fernet.generate_key())
    KEY.chmod(0o600)
BOX = Fernet(KEY.read_bytes())
COOKIE = '__Host-podcast_session'
router = APIRouter()

def db():
    conn = sqlite3.connect(DATA / 'accounts.sqlite', timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

with db() as conn:
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,key TEXT,provider TEXT DEFAULT 'bailian');
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),query TEXT NOT NULL,status TEXT NOT NULL,result TEXT,created_at TEXT NOT NULL,finished_at TEXT);
    CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL,created REAL NOT NULL);
    ''')
    conn.execute("UPDATE tasks SET status='failed',result='服务重启，请重新提交问题。' WHERE status='running'")

def user(request):
    token = hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest()
    with db() as conn:
        row = conn.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?', (token,time.time())).fetchone()
    if not row:
        raise HTTPException(401, '请先登录')
    return dict(row)

def digest(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

async def form(request):
    if request.headers.get('origin') != 'https://podcast.podnotes.cloud':
        raise HTTPException(403, '请从本产品页面提交')
    body = await request.body()
    if len(body) > 8192:
        raise HTTPException(413)
    return {k:v[0] for k,v in parse_qs(body.decode()).items()}

def throttle(request):
    # Gateway replaces, rather than trusts, the incoming client address header.
    ip=request.headers.get('x-real-ip', request.client.host)
    with db() as conn:
        conn.execute('DELETE FROM attempts WHERE created<?',(time.time()-600,))
        count=conn.execute('SELECT count(*) FROM attempts WHERE ip=?',(ip,)).fetchone()[0]
        if count>=20:
            raise HTTPException(429,'操作频繁，请十分钟后重试')
        conn.execute('INSERT INTO attempts VALUES(?,?)',(ip,time.time()))

STYLE='''*{box-sizing:border-box}body{margin:0;background:#f7f3ec;color:#352c25;font:16px/1.7 -apple-system,BlinkMacSystemFont,"Microsoft YaHei",sans-serif}header,main,footer{width:min(1080px,calc(100% - 40px));margin:auto}header{display:flex;align-items:center;justify-content:space-between;padding:26px 0;border-bottom:1px solid #ddd2c3}a{color:#986131;text-decoration:none}nav{display:flex;gap:22px;align-items:center}h1{font-family:Georgia,"Songti SC",serif;font-size:clamp(30px,4vw,48px);line-height:1.4;font-weight:500}h2{font-size:23px;font-weight:600}p{color:#756a5f}main{padding:64px 0}.eyebrow{font-size:12px;letter-spacing:.16em;color:#986131}.button,button{display:inline-block;background:#986131;color:white;border:0;padding:12px 22px;border-radius:5px;font:inherit;cursor:pointer}.secondary{background:transparent;color:#986131;border:1px solid #a9bbb0}.actions{display:flex;gap:14px;flex-wrap:wrap;margin-top:28px}.features{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:30px;margin:64px 0;padding-top:30px;border-top:1px solid #ddd2c3}.features span{color:#986131}.form{max-width:450px;margin:0 auto;padding:30px;border:1px solid #ddd2c3;background:#fff}.form h1{font-size:28px}label{display:block;margin-top:18px}input,select{display:block;width:100%;margin-top:8px;padding:12px;border:1px solid #a9bbb0;border-radius:4px;font:inherit;background:#fff}button{margin-top:24px}footer{padding:24px 0;border-top:1px solid #ddd2c3;color:#657469;font-size:13px}.error{color:#a12f23}input:focus-visible,a:focus-visible,button:focus-visible,select:focus-visible{outline:2px solid #986131;outline-offset:3px}@media(max-width:650px){.features{grid-template-columns:1fr;margin-top:40px;gap:16px}main{padding:36px 0}nav{gap:12px;font-size:14px}.form{padding:22px}}'''

def page(title, content):
    return HTMLResponse('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" type="image/svg+xml" href="/brand/icon.svg?v=20261103-brand1"><link rel="alternate icon" href="/favicon.ico?v=20261103-brand1"><link rel="apple-touch-icon" href="/brand/icon-180.png"><title>'+html.escape(title)+' · 播客手账</title><style>'+STYLE+'</style><header><a href="/" aria-label="播客手账首页" style="display:inline-flex;align-items:center;gap:10px;white-space:nowrap;font-weight:600"><img src="/brand/icon.svg?v=20261103-brand1" width="34" height="34" alt="">播客手账</a><nav><a href="/login">登录</a><a href="/register">注册</a><a href="https://podnotes.cloud/">个人主页</a></nav></header><main>'+content+'</main><footer>听见，理解，留下。AI 辅助整理，内容由你核对。</footer></html>',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})

def auth_page(mode, error=''):
    register=mode=='register'
    title='建立你的播客账号' if register else '回到你的播客工作台'
    fields='<label>用户名<input name="name" required minlength="2" maxlength="40" autocomplete="nickname"></label>' if register else ''
    fields+='<label>邮箱<input name="email" type="email" required maxlength="254" autocomplete="email"></label><label>密码<input name="password" type="password" required minlength="10" maxlength="128" autocomplete="'+('new-password' if register else 'current-password')+'"></label>'
    if register:
        fields+='<label>确认密码<input name="confirmation" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></label>'
    return page(title,'<section class="form"><h1>'+title+'</h1><p class="error" role="alert">'+html.escape(error)+'</p><form method="post" action="/'+mode+'">'+fields+'<button>'+('创建账号' if register else '登录工作台')+' →</button></form><p><a href="/'+('login' if register else 'register')+'">'+('已有账号？立即登录' if register else '还没有账号？免费注册')+'</a></p></section>')

@router.get('/register')
def register_page(): return auth_page('register')

@router.get('/login')
def login_page(): return auth_page('login')

@router.post('/register')
async def register(request:Request):
    values=await form(request);throttle(request)
    email=values.get('email','').strip().lower(); password=values.get('password',''); name=values.get('name','').strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or not 2<=len(name)<=40 or not 10<=len(password)<=128 or password!=values.get('confirmation'):
        return auth_page('register','请填写有效邮箱、用户名，以及两次一致的至少10位密码。')
    salt=secrets.token_hex(16)
    try:
        with db() as conn:
            conn.execute('INSERT INTO users(id,email,name,password) VALUES(?,?,?,?)',(secrets.token_hex(16),email,name,salt+':'+digest(password,salt)))
    except sqlite3.IntegrityError:
        return auth_page('register','该邮箱无法注册，请尝试登录或使用其他邮箱。')
    return auth_page('login','注册成功，请使用新账号登录。')

@router.post('/login')
async def login(request:Request):
    values=await form(request);throttle(request)
    with db() as conn:
        row=conn.execute('SELECT * FROM users WHERE email=?',(values.get('email','').strip().lower(),)).fetchone()
        salt,expected=(row['password'].split(':') if row else ('00'*16,'00'*32))
        actual=digest(values.get('password','')[:128],salt)
        if not row or not hmac.compare_digest(actual,expected):
            return auth_page('login','邮箱或密码不正确。')
        token=secrets.token_urlsafe(48)
        conn.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        conn.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],time.time()+43200))
    response=RedirectResponse('/dashboard',303)
    response.set_cookie(COOKIE,token,max_age=43200,secure=True,httponly=True,samesite='lax',path='/')
    return response

@router.post('/logout')
async def logout(request:Request):
    await form(request)
    with db() as conn:
        conn.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get(COOKIE,'').encode()).hexdigest(),))
    response=RedirectResponse('/login',303);response.delete_cookie(COOKIE,secure=True,httponly=True,path='/');return response

@router.get('/account')
def account(request:Request, error: str = ''):
    try: current=user(request)
    except HTTPException: return RedirectResponse('/login',303)
    from backend.web_llm import ledger
    quota=ledger().status(current['id'])
    status=('个人 Key 已配置，优先使用；留空保留。' if current['key'] else '默认百炼 qwen3.7-flash；运营服务未配置时请自备 Key。')+f" 每账号累计3次AI体验：已用 {quota['used']}，处理中 {quota['reserved']}，剩余 {quota['remaining']}。多段生成共用一次；删除 Key 不重置额度。"
    selected=current['provider']
    options=''.join('<option value="'+v+'"'+(' selected' if selected==v else '')+'>'+n+'</option>' for v,n in [('bailian','百炼 · 北京 qwen3.7-flash'),('deepseek','DeepSeek'),('openai','OpenAI')])
    return page('模型设置','<section class="form"><h1>配置你的模型</h1><p class="error" role="alert">'+html.escape(error)+'</p><p>'+status+'</p><form method="post" action="/account"><label>服务商<select name="provider">'+options+'</select></label><label>API Key<input type="password" name="key" autocomplete="off" maxlength="512" placeholder="输入新 Key，或留空保留"></label><button>保存并验证</button></form><form method="post" action="/account/delete-key"><button class="secondary">删除已保存的 Key</button></form><p>百炼配置：在阿里云百炼北京地域控制台开通按量模型服务，创建 API Key，确认账户余额及 qwen3.7-flash 权限。仅支持北京 Key；其他地域请勿混用。401 请检查 Key，403 检查权限，429 稍后重试或检查限流，余额不足请充值。验证使用个人 Key 的少量付费请求，不占免费次数。请勿在聊天中发送 Key。</p><p><a href="https://bailian.console.aliyun.com/" target="_blank" rel="noopener noreferrer">打开百炼控制台</a></p><p><a href="/dashboard">返回工作台 →</a></p></section>')

@router.post('/account')
async def save_account(request:Request):
    current=user(request);values=await form(request)
    provider=values.get('provider');key=values.get('key','').strip()
    if provider not in ('bailian','deepseek','openai') or len(key)>512:
        raise HTTPException(400,'模型配置无效')
    if key:
        from backend.web_llm import ENDPOINTS
        from starlette.concurrency import run_in_threadpool
        def validate():
            from openai import OpenAI
            endpoint,model=ENDPOINTS[provider]
            params={'model':model,'messages':[{'role':'user','content':'回复 OK'}],'max_tokens':16}
            if provider=='bailian':params['extra_body']={'enable_thinking':False}
            return OpenAI(api_key=key,base_url=endpoint,timeout=20,max_retries=0).chat.completions.create(**params)
        try:await run_in_threadpool(validate)
        except Exception:return account(request,'个人 Key 验证失败，请检查地域、余额、模型权限和 Key 后重试；原配置已保留。')
    with db() as conn:
        if key:
            conn.execute('UPDATE users SET key=?,provider=? WHERE id=?',(BOX.encrypt(key.encode()).decode(),provider,current['id']))
        elif provider!=current['provider']:
            conn.execute('UPDATE users SET key=NULL,provider=? WHERE id=?',(provider,current['id']))
    return RedirectResponse('/account',303)

@router.post('/account/delete-key')
async def delete_key(request:Request):
    current=user(request);await form(request)
    with db() as conn: conn.execute('UPDATE users SET key=NULL WHERE id=?',(current['id'],))
    return RedirectResponse('/account',303)

@router.get('/auth/me')
def me(request:Request):
    current=user(request)
    from backend.web_llm import ledger
    return {'id':current['id'],'name':current['name'],'configured':bool(current['key']),'provider':current['provider'],'quota':ledger().status(current['id'])}
