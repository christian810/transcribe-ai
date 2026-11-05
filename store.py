"""SQLite durable queue. One worker process per deployment."""
import sqlite3
import time
import config as c


def db():
    conn = sqlite3.connect(c.DATA / 'jobs.sqlite', timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    c.DATA.mkdir(parents=True, exist_ok=True)
    (c.DATA / 'jobs').mkdir(exist_ok=True)
    with db() as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, source TEXT, language TEXT, detected TEXT,
            status TEXT, progress INTEGER DEFAULT 0, text TEXT DEFAULT '',
            error TEXT DEFAULT '', created REAL, updated REAL, url TEXT)''')


def update(id, **fields):
    allowed = {'source', 'detected', 'status', 'progress', 'text', 'error'}
    assert set(fields) <= allowed
    fields['updated'] = time.time()
    with db() as con:
        con.execute('UPDATE jobs SET ' + ','.join(f'{k}=?' for k in fields) + ' WHERE id=?',
                    [*fields.values(), id])


def get(id):
    with db() as con:
        row = con.execute('SELECT * FROM jobs WHERE id=?', (id,)).fetchone()
    return dict(row) if row else None


def enqueue(id, source, language, url):
    now = time.time()
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        count = con.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','processing')").fetchone()[0]
        if count >= c.MAX_JOBS:
            raise ValueError('La cola está llena. Inténtalo más tarde.')
        con.execute('INSERT INTO jobs(id,source,language,status,created,updated,url) VALUES(?,?,?,?,?,?,?)',
                    (id, source, language, 'queued', now, now, url))
