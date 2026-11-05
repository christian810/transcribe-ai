import sys
from types import SimpleNamespace
import uuid
import config as c
import store
import worker
from test_media import silent_wav


def test_worker_uses_vad_no_context_and_paragraphs(client, monkeypatch):
    id = uuid.uuid4().hex
    folder = c.DATA / 'jobs' / id
    folder.mkdir()
    silent_wav(folder / 'input.wav')
    store.enqueue(id, 'Formentera.wav', 'ca', '')
    captured = {}

    class Model:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, path, **kwargs):
            captured.update(kwargs)
            segment = SimpleNamespace(text=' Bon dia, Formentera.', start=0, end=1,
                                      no_speech_prob=0.1, avg_logprob=-0.1)
            return iter([segment]), SimpleNamespace(language='ca')
    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=Model))
    monkeypatch.setattr(worker.os, 'setsid', lambda: None)
    worker.process(id)
    assert store.get(id)['text'] == 'Bon dia, Formentera.'
    assert captured['vad_filter'] is True
    assert captured['condition_on_previous_text'] is False
    assert not list(folder.iterdir())
