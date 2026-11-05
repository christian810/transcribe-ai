import io
import time
import uuid
from docx import Document
import config as c
import store
from worker import cleanup


def test_auth_and_csrf(client):
    assert client.get('/', auth=('admin', 'wrong')).status_code == 401
    assert client.get('/').status_code == 200
    assert client.get('/healthz', auth=None).status_code == 200
    assert client.post('/api/jobs', data={'url': 'x'}, headers={'Origin': 'https://evil.test'}).status_code == 403
    for _ in range(15):
        client.get('/', auth=('admin', 'wrong'))
    assert client.get('/').status_code == 429


def test_upload_word_and_edits(client):
    result = client.post('/api/jobs', files={'file': ('../reunion.wav', b'fake-media')}, data={'language': 'ca'})
    assert result.status_code == 202
    id = result.json()['id']
    row = store.get(id)
    assert row['source'] == 'reunion.wav'
    assert (c.DATA / 'jobs' / id / 'input.wav').read_bytes() == b'fake-media'
    assert client.post(f'/api/jobs/{id}/word', json={'text': 'x'}).status_code == 409
    store.update(id, status='done', text='Original', detected='ca')
    edited = 'Bon dia, Formentera.\n\nText revisat amb accents: això, reunió.'
    response = client.post(f'/api/jobs/{id}/word', json={'text': edited})
    assert response.status_code == 200
    assert response.content[:2] == b'PK'
    doc = Document(io.BytesIO(response.content))
    text = '\n'.join(p.text for p in doc.paragraphs)
    assert 'Text revisat amb accents' in text and 'Original' not in text
    assert 'Catalán' in text and 'reunion.wav' in text and 'Fecha de procesamiento' in text
    assert (c.DATA / 'jobs' / id / 'transcripcion.docx').is_file()
    store.init()  # independent SQLite connection/re-initialization preserves finished data
    assert client.get(f'/api/jobs/{id}').json()['text'] == 'Original'


def test_validation(client, monkeypatch):
    assert client.post('/api/jobs').status_code == 422
    assert client.post('/api/jobs', files={'file': ('a.exe', b'x')}).status_code == 415
    assert client.post('/api/jobs', files={'file': ('a.wav', b'')}).status_code == 422
    assert client.post('/api/jobs', files={'file': ('a.wav', b'x')}, data={'url': 'x'}).status_code == 422
    assert client.post('/api/jobs', files={'file': ('a.wav', b'x')}, data={'language': 'en'}).status_code == 422
    monkeypatch.setattr(c, 'MAX_BYTES', 2)
    assert client.post('/api/jobs', files={'file': ('a.wav', b'abc')}).status_code == 413
    assert client.get('/api/jobs/../../etc/passwd').status_code == 404
    assert client.get('/api/jobs/' + 'f' * 32).status_code == 404


def test_youtube_queue(client):
    result = client.post('/api/jobs', data={'url': 'https://youtu.be/abcdefghijk', 'language': 'es'})
    assert result.status_code == 202
    assert store.get(result.json()['id'])['url'] == 'https://www.youtube.com/watch?v=abcdefghijk'
    assert client.post('/api/jobs', data={'url': 'https://127.0.0.1/watch?v=abcdefghijk'}).status_code == 422


def test_queue_limit_and_cleanup(client, monkeypatch):
    monkeypatch.setattr(c, 'MAX_JOBS', 1)
    id = uuid.uuid4().hex
    folder = c.DATA / 'jobs' / id
    folder.mkdir()
    store.enqueue(id, 'test.wav', 'auto', '')
    assert client.post('/api/jobs', files={'file': ('test.wav', b'x')}).status_code == 429
    store.update(id, status='done', text='test')
    with store.db() as con:
        con.execute('UPDATE jobs SET updated=? WHERE id=?', (time.time() - c.RETENTION - 5, id))
    cleanup()
    assert store.get(id) is None and not folder.exists()
