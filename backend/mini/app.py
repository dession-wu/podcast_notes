"""Run with ONE uvicorn worker. Desktop API is intentionally not mounted."""
from contextlib import asynccontextmanager
import hashlib
import logging
import os
from pathlib import Path
import subprocess
import sys
import json
import shutil
import threading
import time

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.mini.estimates import estimates
from backend.mini.network import fetch
from backend.mini.store import Store, WORKER_PROTOCOL

log = logging.getLogger(__name__)


class Login(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class Submission(BaseModel):
    episode_id: str = Field(min_length=1, max_length=128)
    rights_confirmed: bool = False


def public_job(row):
    return {**{key: row[key] for key in ('id', 'title', 'status', 'created', 'error')},
            'timing': json.loads(row.get('timing', '{}'))}


def create_app(data_dir=None, development=None, demo=None, worker=True):
    development = (os.getenv('MINI_DEVELOPMENT') == 'true') if development is None else development
    demo = (os.getenv('MINI_DEMO') == 'true') if demo is None else demo
    if demo and not development:
        raise RuntimeError('演示模式只能在开发模式启用')
    root = Path(data_dir or os.getenv('MINI_DATA_DIR', 'data/miniprogram'))
    root.mkdir(parents=True, exist_ok=True)
    store = Store(root / 'mini.sqlite3')
    storage_id = hashlib.sha256(os.path.normcase(str(Path(store.path).resolve())).encode()).hexdigest()[:16]
    stop = threading.Event()
    daily = int(os.getenv('MINI_DAILY_LIMIT', '3'))
    max_minutes = int(os.getenv('MINI_MAX_MINUTES', '120'))
    retention = int(os.getenv('MINI_RETENTION_DAYS', '7'))
    mode = os.getenv('MINI_TRANSCRIPT_MODE', 'basic')
    if mode not in ('basic', 'dialogue'):
        raise RuntimeError('MINI_TRANSCRIPT_MODE must be basic or dialogue')
    if min(daily, max_minutes, retention) < 1:
        raise RuntimeError('额度、时长与保留天数必须大于零')

    def process(job):
        audio = root / (job['id'] + '.audio')
        started = time.time()
        timing = {'mode': mode, 'started_at': started,
                  'worker_version': WORKER_PROTOCOL, 'worker_pid': os.getpid(),
                  'queue_seconds': max(0, started - job['created'])}
        log.info('Mini task %s started: pid=%s mode=%s protocol=%s',
                 job['id'], os.getpid(), mode, WORKER_PROTOCOL)
        def finish_timing():
            timing['finished_at'] = time.time()
            timing['processing_seconds'] = max(0, timing['finished_at'] - started)
            timing['elapsed_seconds'] = max(0, timing['finished_at'] - job['created'])
        try:
            segments = []
            ep = store.get(job['episode'], 'episode')
            if not ep:
                raise ValueError('节目资料已失效，请重新搜索')
            if demo:
                text = '【演示内容，并非真实播客转写】\n\n' + ep['title'] + '\n\n[00:00] 欢迎体验播客文字工具。\n[00:10] 搜索、选择单集并提交后，可在任务页查看处理结果。\n[00:20] 这里可以阅读、复制文字，并导出 TXT。'
            else:
                timing['download_started_at'] = time.time()
                store.update(job['id'], 'downloading', timing=timing)
                fetch(ep['audio_url'], 150 * 1024 * 1024, audio)
                timing['download_seconds'] = max(0, time.time() - timing['download_started_at'])
                probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio)], capture_output=True, text=True, timeout=30, check=True)
                duration = float(probe.stdout.strip())
                timing['audio_duration_seconds'] = duration
                if not 0 < duration <= max_minutes * 60:
                    raise ValueError(f'音频时长须在 {max_minutes} 分钟以内')
                timing['transcription_started_at'] = time.time()
                store.update(job['id'], 'transcribing', timing=timing)
                spec = root / (job['id'] + '.json')
                output = root / (job['id'] + '.txt')
                work = root / (job['id'] + '.work')
                work.mkdir(exist_ok=True)
                spec.write_text(json.dumps({**ep, 'local_audio_path': str(audio.resolve())}), encoding='utf-8')
                subprocess.run([sys.executable, '-m', 'backend.mini.transcribe_worker', str(spec.resolve()), str(output.resolve())],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=int(os.getenv('MINI_TRANSCRIBE_TIMEOUT', '7200')), check=True,
                               env={**os.environ, 'DATA_DIR': str(work.resolve()), 'TEMP_DIR': str(work.resolve()),
                                    'ENABLE_SPEAKER_DIARIZATION': 'false', 'MINI_TRANSCRIPT_MODE': mode})
                timing['transcription_seconds'] = max(0, time.time() - timing['transcription_started_at'])
                text = output.read_text(encoding='utf-8')
                structured = output.with_suffix('.segments.json')
                if structured.exists():
                    segments = json.loads(structured.read_text(encoding='utf-8'))['segments']
                if mode == 'dialogue' and not segments:
                    raise ValueError('对话模式未生成时间和说话人片段，请检查服务版本及转写日志')
                if not text.strip():
                    raise ValueError('未识别出文字，请检查音频')
            finish_timing()
            store.update(job['id'], 'completed', text=text, segments=segments, timing=timing)
            log.info('Mini task %s completed: segments=%s elapsed=%.1fs',
                     job['id'], len(segments), timing['elapsed_seconds'])
        except Exception as error:
            # Avoid logging signed upstream URLs, credentials or transcript content.
            log.error('Mini task %s failed (%s)', job['id'], type(error).__name__)
            message = str(error) if isinstance(error, ValueError) else '处理失败，请检查转写引擎与网络后重新提交'
            finish_timing()
            store.update(job['id'], 'failed', error=message, timing=timing)
        finally:
            shutil.rmtree(root / (job['id'] + '.work'), ignore_errors=True)
            for suffix in ('.audio', '.json', '.txt', '.segments.json'):
                (root / (job['id'] + suffix)).unlink(missing_ok=True)

    def run():
        store.recover()
        # Remove audio left by a hard kill; this directory belongs only to this service.
        for pattern in ('*.audio', '*.json', '*.txt'):
            for item in root.glob(pattern):
                item.unlink(missing_ok=True)
        for item in root.glob('*.work'):
            shutil.rmtree(item, ignore_errors=True)
        while not stop.is_set():
            with store.db() as db:
                db.execute("UPDATE ai_operations SET result='' WHERE job IN (SELECT id FROM jobs WHERE created<? AND status IN ('completed','failed','deleted'))", (time.time() - retention * 86400,))
                db.execute("DELETE FROM jobs WHERE created<? AND status IN ('completed','failed','deleted')", (time.time() - retention * 86400,))
            job = store.claim()
            if job:
                process(job)
            else:
                stop.wait(1)

    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=run, daemon=True)
        app.state.worker_thread = thread
        if worker:
            app.state.ai.recover()
            thread.start()
        yield
        stop.set()
        if worker:
            thread.join(timeout=2)
        app.state.ai.pool.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(title='Podcast Notes Mini API', lifespan=lifespan, docs_url='/docs' if development else None, redoc_url=None, openapi_url='/openapi.json' if development else None)
    app.state.store = store
    app.state.process = process
    app.state.worker_thread = None

    def rate(key, limit):
        minute = int(time.time() // 60)
        with store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS rates (key TEXT, minute INT, count INT, PRIMARY KEY(key,minute))')
            db.execute('DELETE FROM rates WHERE minute<?', (minute - 2,))
            db.execute('INSERT INTO rates VALUES (?,?,1) ON CONFLICT(key,minute) DO UPDATE SET count=count+1', (key, minute))
            count = db.execute('SELECT count FROM rates WHERE key=? AND minute=?', (key, minute)).fetchone()[0]
        if count > limit:
            raise HTTPException(429, '操作太频繁，请稍后重试')

    @app.middleware('http')
    async def local_only(request, call_next):
        if development and request.client and request.client.host not in ('127.0.0.1', '::1', 'testclient'):
            return Response('Development service is loopback only', status_code=403)
        if request.headers.get('content-length', '0').isdigit() and int(request.headers.get('content-length', '0')) > 4096:
            return Response('Request too large', status_code=413)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def owner(authorization: str = Header(default='')):
        token = authorization.removeprefix('Bearer ')
        value = store.owner(token) if authorization.startswith('Bearer ') else None
        if not value:
            raise HTTPException(401, '登录已过期，请重新进入')
        rate(value, 90)
        return value

    @app.get('/mini/health')
    def health():
        return {'status': 'ok', 'development': development, 'demo': demo,
                'transcript_mode': mode, 'transcript_format_version': 2,
                'runtime_diagnostics_version': 4, 'storage_id': storage_id,
                'worker_protocol': WORKER_PROTOCOL,
                'worker_alive': bool(app.state.worker_thread and app.state.worker_thread.is_alive())}

    @app.post('/mini/login')
    async def login(body: Login, request: Request):
        rate('login:' + (request.client.host if request.client else 'unknown'), 20)
        if development:
            if not body.code.startswith('dev:') or len(body.code) < 20:
                raise HTTPException(400, '开发登录凭证无效')
            identity = 'dev:' + hashlib.sha256(body.code.encode()).hexdigest()
        else:
            appid, secret = os.getenv('WECHAT_APP_ID'), os.getenv('WECHAT_APP_SECRET')
            if not appid or not secret:
                raise HTTPException(503, '微信登录尚未配置')
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    res = await client.get('https://api.weixin.qq.com/sns/jscode2session', params={'appid': appid, 'secret': secret, 'js_code': body.code, 'grant_type': 'authorization_code'})
                    res.raise_for_status()
                    payload = res.json()
            except (httpx.HTTPError, ValueError):
                raise HTTPException(502, '微信登录暂不可用，请稍后重试') from None
            if payload.get('errcode') or not payload.get('openid'):
                # Only expose a numeric upstream error; never log credentials or payloads.
                errcode = payload.get('errcode')
                if isinstance(errcode, int) and not isinstance(errcode, bool):
                    log.warning('WeChat login rejected: errcode=%s', errcode)
                    raise HTTPException(401, f'微信登录失败（错误码 {errcode}）')
                raise HTTPException(401, '微信登录失败，请重试')
            identity = 'wx:' + hashlib.sha256(payload['openid'].encode()).hexdigest()
        return {'token': store.session(identity), 'expires_in': 86400, 'demo': demo, 'daily_limit': daily, 'max_minutes': max_minutes, 'retention_days': retention}

    @app.get('/mini/session')
    def current_session(user=Depends(owner)):
        return {'demo': demo, 'daily_limit': daily, 'max_minutes': max_minutes, 'retention_days': retention}

    @app.get('/mini/search')
    async def search(q: str = '', user=Depends(owner)):
        term = q.strip()
        if not 1 <= len(term) <= 80:
            raise HTTPException(422, '请输入 1—80 字的播客名称')
        rate('search:' + user, 10)
        if demo:
            records = [{'title': '播客文字体验节目（演示）', 'author': '本地演示', 'rss_url': 'demo://feed'}]
        else:
            from services.podcast_search import PodcastSearcher
            try:
                records = [vars(r) for r in await PodcastSearcher().search(term, max_results=10)]
            except Exception:
                raise HTTPException(502, '搜索来源暂不可用，请稍后重试') from None
        return {'results': [{'id': store.put('feed', r), 'title': r['title'], 'author': r.get('author', '')} for r in records]}

    @app.get('/mini/feeds/{feed_id}/episodes')
    def episodes(feed_id: str, page: int = 1, user=Depends(owner)):
        if not 1 <= page <= 500:
            raise HTTPException(422, '页码无效')
        rate('feed:' + user, 10)
        feed = store.get(feed_id, 'feed')
        if not feed:
            raise HTTPException(404, '节目不存在，请重新搜索')
        if demo:
            items = [{'title': '第一期：把声音变成文字（演示）', 'audio_url': 'demo://audio', 'feed_title': feed['title'], 'duration_seconds': 60}]
        else:
            import feedparser
            from core.audio_downloader import AudioDownloader
            try:
                parsed = feedparser.parse(fetch(feed['rss_url'], 5 * 1024 * 1024))
                parser = AudioDownloader(download_dir=root)
                items = [ep.model_dump(mode='json', exclude={'local_audio_path'}) for entry in parsed.entries[:10000] if (ep := parser._parse_entry(entry, feed['title'], feed['rss_url']))]
            except Exception:
                raise HTTPException(502, '无法读取节目列表，请稍后重试') from None
        batch = items[(page - 1) * 20:page * 20]
        return {'title': feed['title'], 'has_more': page * 20 < len(items), 'episodes': [{'id': store.put('episode', ep), 'title': ep['title'], 'duration_seconds': ep.get('duration_seconds')} for ep in batch]}

    def presented(rows):
        values = estimates(rows, store.estimate_snapshot(mode), mode)
        return [{**public_job(row), 'estimate': values[row['id']]} for row in rows]

    @app.post('/mini/tasks', status_code=202)
    def submit(body: Submission, user=Depends(owner)):
        if not body.rights_confirmed:
            raise HTTPException(422, '请确认拥有处理该内容所需的权利或授权')
        ep = store.get(body.episode_id, 'episode')
        if not ep:
            raise HTTPException(404, '单集不存在，请重新搜索')
        if (ep.get('duration_seconds') or 0) > max_minutes * 60:
            raise HTTPException(422, f'单集超过 {max_minutes} 分钟限制')
        try:
            return presented([store.admit(user, body.episode_id, ep['title'], daily=daily)])[0]
        except ValueError as error:
            raise HTTPException(429, str(error)) from None

    @app.get('/mini/tasks')
    def tasks(user=Depends(owner)):
        return {'tasks': presented([r for r in store.listing(user) if r['status'] != 'deleted'])}

    def owned(key, user):
        row = store.job(key, user)
        if not row or row['status'] == 'deleted':
            raise HTTPException(404, '任务不存在')
        return row

    @app.get('/mini/tasks/{key}')
    def task(key: str, user=Depends(owner)):
        row = owned(key, user)
        complete = row['status'] == 'completed'
        return {**presented([row])[0], 'text': row['text'] if complete else '',
                'segments': json.loads(row['segments']) if complete else []}

    @app.get('/mini/tasks/{key}/export')
    def export(key: str, user=Depends(owner)):
        row = owned(key, user)
        if row['status'] != 'completed':
            raise HTTPException(409, '文字尚未生成')
        return Response('\ufeff' + row['text'], media_type='text/plain; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="podcast-{key}.txt"', 'Cache-Control': 'no-store'})

    @app.delete('/mini/tasks/{key}', status_code=204)
    def delete(key: str, user=Depends(owner)):
        owned(key, user)
        try:
            store.delete(key, user)
            app.state.ai.delete_result(key, user)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        return Response(status_code=204)

    from backend.mini.ai import install as install_ai
    install_ai(app, store, root, owner)
    return app


# Factory mode avoids creating a database merely by importing this module in tests.
