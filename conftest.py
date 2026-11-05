import pytest
import config as c
import store
from main import app, failures
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(c, 'DATA', tmp_path)
    monkeypatch.setattr(c, 'PASSWORD', 'test-password-long-enough')
    monkeypatch.setattr(c, 'USER', 'admin')
    monkeypatch.setattr(c, 'AUTH_REQUIRED', True)
    store.init()
    failures.clear()
    # No lifespan: worker intentionally disabled for deterministic API tests.
    client = TestClient(app, base_url='http://localhost', client=('192.168.5.21', 50000))
    client.auth = ('admin', 'test-password-long-enough')
    return client
