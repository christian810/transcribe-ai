import os
from pathlib import Path

DATA = Path(os.getenv('DATA_DIR', '/data'))
MODELS = Path(os.getenv('MODELS_DIR', '/models'))
MAX_BYTES = int(os.getenv('MAX_UPLOAD_MB', '500')) * 1024 * 1024
MAX_SECONDS = int(os.getenv('MAX_AUDIO_SECONDS', '14400'))
JOB_TIMEOUT = int(os.getenv('JOB_TIMEOUT_SECONDS', '21600'))
RETENTION = int(os.getenv('RETENTION_HOURS', '24')) * 3600
MAX_JOBS = int(os.getenv('MAX_QUEUED_JOBS', '8'))
MODEL = os.getenv('WHISPER_MODEL', 'small')
DEVICE = os.getenv('WHISPER_DEVICE', 'cpu')
COMPUTE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
USER = os.getenv('APP_USER', 'admin')
PASSWORD = os.getenv('APP_PASSWORD', '')
EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4', '.mkv', '.mov', '.webm'}

PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', '').rstrip('/')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
