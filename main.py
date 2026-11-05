import asyncio
from contextlib import asynccontextmanager
import secrets
import shutil
import threading
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
import config as c
import store
from documents import build_word
from security import youtube_url
from worker import loop

basic = HTTPBasic()
failures = {}


def auth(request: Request, credentials: HTTPBasicCredentials = Depends(basic)):
    ip = request.client.host if request.client else 'local'
    now = time.monotonic()
    with auth_lock:
        # Bounded retry table; do not retain client addresses indefinitely.
        for key in list(failures):
            if now - failures[key][1] > 300:
                del failures[key]
        count, _ = failures.get(ip, (0, now))
        if count >= 15:
            raise HTTPException(429, 'Demasiados intentos. Espera cinco minutos.')
        valid_user = secrets.compare_digest(credentials.username.encode(), c.USER.encode())
        valid_password = secrets.compare_digest(credentials.password.encode(), c.PASSWORD.encode())
        if not (valid_user and valid_password):
            if len(failures) >= 10000:
                failures.clear()
            failures[ip] = (count + 1, now)
            raise HTTPException(401, 'Acceso no válido', headers={'WWW-Authenticate': 'Basic realm="Transcribe AI"'})
        failures.pop(ip, None)
    return credentials.username


auth_lock = threading.Lock()
upload_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app):
    if len(c.PASSWORD) < 16:
        raise RuntimeError('APP_PASSWORD debe contener al menos 16 caracteres. Ejecuta install.sh.')
    store.init()
    stop = threading.Event()
    worker = threading.Thread(target=loop, args=(stop,), daemon=True)
    worker.start()
    yield
    stop.set()
    worker.join(timeout=15)


app = FastAPI(title='Transcribe AI', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


class BodyLimit:
    """Bound raw multipart before Starlette spools uploads. Count actual streamed bytes."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        maximum = c.MAX_BYTES + 1024 * 1024 if scope['path'] == '/api/jobs' else 2 * 1024 * 1024
        size = 0

        async def bounded():
            nonlocal size
            message = await receive()
            size += len(message.get('body', b''))
            if size > maximum:
                raise HTTPException(413, 'El archivo supera el límite configurado.')
            return message
        length = dict(scope.get('headers', [])).get(b'content-length', b'0')
        try:
            if int(length) > maximum:
                return await JSONResponse({'detail': 'El archivo supera el límite configurado.'}, 413)(scope, receive, send)
        except ValueError:
            return await JSONResponse({'detail': 'Content-Length no válido'}, 400)(scope, receive, send)
        await self.app(scope, bounded, send)


app.add_middleware(BodyLimit)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=c.ALLOWED_HOSTS)


@app.middleware('http')
async def headers(request, call_next):
    if request.method in {'POST', 'PUT', 'DELETE', 'PATCH'}:
        # Basic auth is browser-ambient: reject cross-origin writes including login CSRF.
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Origen no permitido'}, 403)
        origin = request.headers.get('origin')
        if origin and origin != (c.PUBLIC_ORIGIN or str(request.base_url).rstrip('/')):
            return JSONResponse({'detail': 'Origen no permitido'}, 403)
    if request.url.path != '/healthz' and not request.url.path.startswith('/static/'):
        try:
            auth(request, await basic(request))
        except HTTPException as exc:
            return JSONResponse({'detail': exc.detail}, exc.status_code, headers=exc.headers)
    response = await call_next(request)
    response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
    return response


@app.get('/healthz')
def health():
    return {'status': 'ok'}


@app.get('/', dependencies=[Depends(auth)])
def index():
    return FileResponse(Path(__file__).parent / 'index.html')


@app.get('/api/config', dependencies=[Depends(auth)])
def limits():
    return {'max_upload_mb': c.MAX_BYTES // (1024 * 1024), 'max_minutes': c.MAX_SECONDS // 60}


@app.post('/api/jobs', dependencies=[Depends(auth)], status_code=202)
async def create_job(file: UploadFile | None = File(None), url: str = Form(''), language: str = Form('auto')):
    if language not in {'auto', 'es', 'ca'}:
        raise HTTPException(422, 'Idioma no válido')
    if bool(file and file.filename) == bool(url.strip()):
        raise HTTPException(422, 'Selecciona un archivo o un enlace de YouTube.')
    try:
        canonical = youtube_url(url.strip()) if url.strip() else ''
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    id = uuid.uuid4().hex
    folder = c.DATA / 'jobs' / id
    if upload_lock.locked():
        raise HTTPException(429, 'Se está guardando otro archivo. Inténtalo en unos segundos.')
    async with upload_lock:
        folder.mkdir(mode=0o700)
        try:
            source = 'YouTube'
            if file and file.filename:
                source = Path(file.filename.replace('\\', '/')).name[:250]
                extension = Path(source).suffix.lower()
                if extension not in c.EXTENSIONS:
                    raise HTTPException(415, 'Formato no permitido')
                size = 0
                with (folder / ('input' + extension)).open('wb') as output:
                    while chunk := await file.read(1024 * 1024):
                        size += len(chunk)
                        if size > c.MAX_BYTES:
                            raise HTTPException(413, 'Archivo demasiado grande')
                        output.write(chunk)
                if not size:
                    raise HTTPException(422, 'El archivo está vacío')
            store.enqueue(id, source, language, canonical)
        except BaseException as exc:
            shutil.rmtree(folder, ignore_errors=True)
            if isinstance(exc, ValueError):
                raise HTTPException(429, str(exc)) from None
            raise
        finally:
            if file:
                await file.close()
    return {'id': id}


def find_job(id):
    if not len(id) == 32 or any(ch not in '0123456789abcdef' for ch in id):
        raise HTTPException(404, 'Trabajo no encontrado')
    row = store.get(id)
    if not row:
        raise HTTPException(404, 'Trabajo no encontrado o caducado')
    return row


@app.get('/api/jobs/{id}', dependencies=[Depends(auth)])
def job(id: str):
    row = find_job(id)
    return {key: row[key] for key in ('id', 'source', 'language', 'detected', 'status', 'progress', 'text', 'error')}


class EditedText(BaseModel):
    text: str = Field(max_length=500000)


@app.post('/api/jobs/{id}/word', dependencies=[Depends(auth)])
def word(id: str, body: EditedText):
    row = find_job(id)
    if row['status'] != 'done':
        raise HTTPException(409, 'La transcripción aún no está terminada')
    content = build_word(row, body.text)
    # Unique file prevents concurrent export races; response uses immutable bytes.
    folder = c.DATA / 'jobs' / id
    try:
        (folder / 'transcripcion.docx').write_bytes(content)
    except FileNotFoundError:
        raise HTTPException(410, 'El trabajo ha caducado') from None
    return Response(content, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    headers={'Content-Disposition': 'attachment; filename="transcripcion.docx"'})


@app.get('/static/{asset}')
def static_asset(asset: str):
    if asset not in {'app.js', 'style.css'}:
        raise HTTPException(404)
    return FileResponse(Path(__file__).parent / asset)
