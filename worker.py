import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time
import config as c
import store
from media import normalize
from security import start_proxy


def download(url, folder):
    proxy = start_proxy()
    address = f'http://127.0.0.1:{proxy.server_port}'
    args = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist', '--no-cache-dir',
            '--proxy', address, '--socket-timeout', '20', '--retries', '2', '--no-progress',
            '--js-runtimes', 'node', '--extractor-args', 'youtube:player_client=default',
            '--max-filesize', str(c.MAX_BYTES), '--match-filters',
            f'duration <= {c.MAX_SECONDS} & !is_live', '-f', 'bestaudio[ext=m4a]/bestaudio',
            '--write-info-json', '-o', str(folder / 'youtube.%(ext)s'), url]
    try:
        # yt-dlp handles HTTPS through our DNS-pinning proxy, no generic extractor or user options.
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True, timeout=1800,
                       env={**os.environ, 'NO_PROXY': '', 'no_proxy': ''})
        info = json.loads((folder / 'youtube.info.json').read_text())
        candidates = [p for p in folder.glob('youtube.*') if p.suffix not in {'.json', '.part', '.ytdl'}]
        if len(candidates) != 1 or candidates[0].stat().st_size > c.MAX_BYTES:
            raise ValueError()
        return candidates[0], str(info.get('title', 'YouTube'))[:250]
    except (subprocess.SubprocessError, ValueError, OSError):
        raise ValueError('YouTube no permite descargar este vídeo o se ha superado un límite. Puedes subir el archivo si tienes autorización.') from None
    finally:
        proxy.shutdown()
        proxy.server_close()


def process(id):
    # Each job owns a process group so watchdog can stop decoder, downloader and descendants.
    if hasattr(os, 'setsid'):
        os.setsid()
    folder = c.DATA / 'jobs' / id
    try:
        row = store.get(id)
        store.update(id, status='processing', progress=5)
        source = next(folder.glob('input.*'), None)
        if row['url']:
            source, title = download(row['url'], folder)
            store.update(id, source=title)
        if source is None:
            raise ValueError('No se encuentra el archivo de entrada.')
        store.update(id, progress=15)
        wav = folder / 'audio.wav'
        duration = normalize(source, wav)
        store.update(id, progress=25)
        from faster_whisper import WhisperModel
        model = WhisperModel(c.MODEL, device=c.DEVICE, compute_type=c.COMPUTE,
                             cpu_threads=int(os.getenv('WHISPER_CPU_THREADS', '4')),
                             download_root=str(c.MODELS),
                             local_files_only=os.getenv('MODEL_OFFLINE', 'false').lower() == 'true')
        segments, info = model.transcribe(str(wav), language=None if row['language'] == 'auto' else row['language'],
            beam_size=5, vad_filter=True, vad_parameters={'min_silence_duration_ms': 500},
            condition_on_previous_text=False, no_speech_threshold=0.6,
            hallucination_silence_threshold=2, word_timestamps=True)
        paragraphs, group = [], []
        last_end = 0
        for segment in segments:
            text = segment.text.strip()
            if text and not (segment.no_speech_prob > 0.6 and segment.avg_logprob < -1):
                if group and (segment.start - last_end > 1.5 or len(' '.join(group)) > 650):
                    paragraphs.append(' '.join(group))
                    group = []
                group.append(text)
                last_end = segment.end
            store.update(id, progress=min(95, 25 + int(70 * segment.end / duration)))
        if group:
            paragraphs.append(' '.join(group))
        store.update(id, status='done', progress=100, text='\n\n'.join(paragraphs),
                     detected=info.language if paragraphs else 'Sin voz detectada')
    except Exception as exc:
        # Deliberately omit raw decoder/model exceptions and paths from client responses.
        message = str(exc) if isinstance(exc, ValueError) else 'No se pudo transcribir. Revisa los recursos del servidor y la disponibilidad del modelo.'
        store.update(id, status='error', error=message[:500])
    finally:
        for p in folder.iterdir():
            if p.is_file():
                p.unlink(missing_ok=True)  # Remove original audio immediately, even after errors.


def cleanup():
    with store.db() as con:
        rows = con.execute("SELECT id FROM jobs WHERE status IN ('done','error') AND updated < ?",
                           (time.time() - c.RETENTION,)).fetchall()
        for row in rows:
            shutil.rmtree(c.DATA / 'jobs' / row['id'], ignore_errors=True)
            con.execute('DELETE FROM jobs WHERE id=?', (row['id'],))
    # Clean abandoned uploads (never enqueued), including interrupted requests.
    for folder in (c.DATA / 'jobs').iterdir():
        if folder.is_dir() and time.time() - folder.stat().st_mtime > 3600 and not store.get(folder.name):
            shutil.rmtree(folder, ignore_errors=True)


def loop(stop):
    with store.db() as con:
        con.execute("UPDATE jobs SET status='queued', progress=0 WHERE status='processing'")
    while not stop.is_set():
        cleanup()
        with store.db() as con:
            row = con.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:
            stop.wait(2)
            continue
        id = row['id']
        child = mp.get_context('spawn').Process(target=process, args=(id,))
        child.start()
        started = time.monotonic()
        while child.is_alive() and not stop.wait(0.5) and time.monotonic() - started < c.JOB_TIMEOUT:
            # Enforce disk bound even when upstream has no Content-Length / filesize metadata.
            size = sum(p.stat().st_size for p in (c.DATA / 'jobs' / id).glob('youtube.*') if p.is_file())
            if size > c.MAX_BYTES + 1024 * 1024:
                break
        if child.is_alive():
            import signal
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.join(5)
            store.update(id, status='error', error='Trabajo detenido por tiempo, tamaño o reinicio. Vuelve a intentarlo.')
        elif store.get(id)['status'] not in {'done', 'error'}:
            store.update(id, status='error', error='El proceso terminó inesperadamente. Comprueba la memoria disponible.')
        child.join()
        # A hard kill skips child cleanup.
        for p in (c.DATA / 'jobs' / id).iterdir():
            if p.is_file() and p.suffix != '.docx':
                p.unlink(missing_ok=True)
