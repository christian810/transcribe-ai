import json
import subprocess
from pathlib import Path
import config as c


def run(args, timeout=120):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise ValueError('No se pudo procesar el audio. Comprueba el formato, la duración y que no esté dañado.') from None


def normalize(source: Path, target: Path):
    # Only local files/pipe; embedded network references in malicious playlists are rejected.
    probe = json.loads(run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                            '-show_format', '-show_streams', '-of', 'json', str(source)]))
    duration = float(probe.get('format', {}).get('duration', 0))
    if duration <= 0 or duration > c.MAX_SECONDS:
        raise ValueError(f'El audio debe durar entre 1 segundo y {c.MAX_SECONDS // 60} minutos.')
    if not any(s.get('codec_type') == 'audio' for s in probe.get('streams', [])):
        raise ValueError('El archivo no contiene una pista de audio.')
    run(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-y', '-i',
         str(source), '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000', '-t',
         str(c.MAX_SECONDS), '-fs', str(c.MAX_SECONDS * 32000 + 4096), str(target)], timeout=600)
    return duration
