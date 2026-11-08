"""SQLite ownership, durable queue and atomic admission controls."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

WORKER_PROTOCOL = 4


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (hash TEXT PRIMARY KEY, owner TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS catalog (id TEXT PRIMARY KEY, kind TEXT, payload TEXT);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, owner TEXT, episode TEXT, title TEXT,
                    day TEXT, created REAL, status TEXT, text TEXT DEFAULT '', error TEXT DEFAULT '');
                CREATE INDEX IF NOT EXISTS jobs_owner ON jobs(owner, created);
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(jobs)')}
            if 'segments' not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN segments TEXT NOT NULL DEFAULT '[]'")
            if 'timing' not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN timing TEXT NOT NULL DEFAULT '{}'")
            if 'claim_version' not in columns:
                db.execute('ALTER TABLE jobs ADD COLUMN claim_version INTEGER NOT NULL DEFAULT 0')
            if 'claim_pid' not in columns:
                db.execute('ALTER TABLE jobs ADD COLUMN claim_pid INTEGER')
            # Enforce at the shared database boundary: pre-upgrade Python processes
            # may still have old Store.claim code loaded in memory.
            db.execute(f'''CREATE TRIGGER IF NOT EXISTS mini_claim_protocol_v4
                BEFORE UPDATE OF status ON jobs
                WHEN OLD.status='queued' AND NEW.status='downloading'
                     AND NEW.claim_version < {WORKER_PROTOCOL}
                BEGIN
                    SELECT RAISE(ABORT, 'Legacy mini worker cannot claim tasks; upgrade required');
                END''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def session(self, owner):
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), owner, time.time() + 86400))
        return token

    def owner(self, token):
        with self.db() as db:
            row = db.execute('SELECT owner FROM sessions WHERE hash=? AND expires>?',
                             (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        return row['owner'] if row else None

    def put(self, kind, payload):
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        key = hashlib.sha256((kind + raw).encode()).hexdigest()
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO catalog VALUES (?,?,?)', (key, kind, raw))
        return key

    def get(self, key, kind):
        with self.db() as db:
            row = db.execute('SELECT payload FROM catalog WHERE id=? AND kind=?', (key, kind)).fetchone()
        return json.loads(row['payload']) if row else None

    def admit(self, owner, episode, title, daily=3, active=1, capacity=20):
        day = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT * FROM jobs WHERE owner=? AND status IN ('queued','downloading','transcribing')", (owner,)).fetchall()
            for row in rows:
                if row['episode'] == episode:
                    return dict(row)
            if len(rows) >= active:
                raise ValueError('已有任务处理中，请完成后再试')
            count = db.execute('SELECT COUNT(*) FROM jobs WHERE owner=? AND day=?', (owner, day)).fetchone()[0]
            if count >= daily:
                raise ValueError('今日转写额度已用完，请明天再试')
            count = db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','downloading','transcribing')").fetchone()[0]
            if count >= capacity:
                raise ValueError('当前排队人数较多，请稍后再试')
            key = secrets.token_hex(16)
            db.execute('INSERT INTO jobs(id,owner,episode,title,day,created,status) VALUES (?,?,?,?,?,?,?)',
                       (key, owner, episode, title, day, time.time(), 'queued'))
            return dict(db.execute('SELECT * FROM jobs WHERE id=?', (key,)).fetchone())

    def job(self, key, owner):
        with self.db() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND owner=?', (key, owner)).fetchone()
        return dict(row) if row else None

    def listing(self, owner):
        with self.db() as db:
            return [dict(row) for row in db.execute('SELECT id,title,episode,created,status,error,timing FROM jobs WHERE owner=? ORDER BY created DESC LIMIT 100', (owner,))]

    def update(self, key, status, text='', error='', segments=None, timing=None):
        with self.db() as db:
            db.execute('UPDATE jobs SET status=?,text=?,error=?,segments=?,timing=COALESCE(?,timing) WHERE id=?',
                       (status, text, error, json.dumps(segments or [], ensure_ascii=False),
                        json.dumps(timing) if timing is not None else None, key))

    def recover(self):
        with self.db() as db:
            db.execute("UPDATE jobs SET status='failed',error='服务重启中断了处理，请重新提交' WHERE status IN ('downloading','transcribing')")

    def claim(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE jobs SET status='downloading',claim_version=?,claim_pid=? WHERE id=?",
                           (WORKER_PROTOCOL, os.getpid(), row['id']))
                row = db.execute('SELECT * FROM jobs WHERE id=?', (row['id'],)).fetchone()
            return dict(row) if row else None

    def delete(self, key, owner):
        with self.db() as db:
            row = db.execute('SELECT status FROM jobs WHERE id=? AND owner=?', (key, owner)).fetchone()
            if not row:
                return False
            if row['status'] not in ('completed', 'failed'):
                raise ValueError('任务处理期间无法删除')
            # Preserve the admission row until daily quota expires; remove personal content now.
            db.execute("UPDATE jobs SET status='deleted',text='',segments='[]',timing='{}',title='',error='',episode='' WHERE id=?", (key,))
            return True

    def estimate_snapshot(self, mode):
        """Read only timing/catalog metadata, in one consistent SQLite snapshot."""
        with self.db() as db:
            db.execute('BEGIN')
            active = [dict(r) for r in db.execute("SELECT id,episode,created,status,timing FROM jobs WHERE status IN ('queued','downloading','transcribing') ORDER BY created,id")]
            history = [dict(r) for r in db.execute("SELECT timing FROM jobs WHERE status='completed' AND json_valid(timing) AND json_extract(timing, '$.mode')=? ORDER BY created DESC,id DESC LIMIT 30", (mode,))]
            episodes = {r['id']: json.loads(r['payload']) for r in db.execute("SELECT id,payload FROM catalog WHERE kind='episode' AND id IN (SELECT episode FROM jobs WHERE status IN ('queued','downloading','transcribing'))")}
        return active, history, episodes
