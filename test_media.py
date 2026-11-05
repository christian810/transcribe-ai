import subprocess
import wave
import pytest
from media import normalize
import config as c


def silent_wav(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\x00\x00' * 32000)


def test_wav_and_video_extraction(tmp_path):
    source = tmp_path / 'source.wav'
    silent_wav(source)
    for extension in ('mp3', 'm4a', 'flac', 'ogg', 'mp4', 'mkv', 'mov', 'webm'):
        file = tmp_path / ('input.' + extension)
        codec = ['-c:a', 'libopus'] if extension == 'webm' else []
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), *codec, str(file)], check=True)
        wav = tmp_path / (extension + '.wav')
        assert normalize(file, wav) > 0
        with wave.open(str(wav)) as audio:
            assert audio.getnchannels() == 1 and audio.getframerate() == 16000
    # Real video track plus audio, not just an audio stream inside a video container.
    video = tmp_path / 'video.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=size=160x90:rate=10',
                    '-i', str(source), '-t', '2', '-c:v', 'mpeg4', '-c:a', 'aac', str(video)], check=True)
    assert normalize(video, tmp_path / 'video.wav') >= 2


def test_corrupt_and_too_long(tmp_path, monkeypatch):
    source = tmp_path / 'invalid.mp3'
    source.write_bytes(b'not really audio')
    with pytest.raises(ValueError):
        normalize(source, tmp_path / 'out.wav')
    silent_wav(source)
    monkeypatch.setattr(c, 'MAX_SECONDS', 1)
    with pytest.raises(ValueError):
        normalize(source, tmp_path / 'out.wav')
