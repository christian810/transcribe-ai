import socket
import pytest
from security import youtube_url, allowed_host, public_addresses, start_proxy


@pytest.mark.parametrize('url', ['http://youtu.be/abcdefghijk', 'https://youtube.com.evil.test/watch?v=abcdefghijk',
    'https://youtube.com@127.0.0.1/watch?v=abcdefghijk', 'https://youtube.com:8443/watch?v=abcdefghijk',
    'https://youtube.com/redirect?q=http://127.0.0.1', 'file:///etc/passwd',
    'https://youtu.be/../../etc/passwd', 'https://youtu.be/abcdefghijk#fragment',
    'https://www.youtube.com/playlist?list=abc'])
def test_bad_urls(url):
    with pytest.raises(ValueError):
        youtube_url(url)


def test_allowlist():
    assert allowed_host('rr1.googlevideo.com')
    assert not allowed_host('evilgooglevideo.com')
    assert not allowed_host('googlevideo.com.evil.test')
    assert youtube_url('https://www.youtube.com/watch?v=abcdefghijk&list=abc').endswith('v=abcdefghijk')


@pytest.mark.parametrize('ip', ['127.0.0.1', '192.168.0.1', '169.254.169.254', '::1', 'fc00::1', '10.0.0.1'])
def test_private_resolution(monkeypatch, ip):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))])
    with pytest.raises(ValueError):
        public_addresses('www.youtube.com', 443)


def test_proxy_rejects_non_allowlisted_target():
    proxy = start_proxy()
    try:
        with socket.create_connection(proxy.server_address) as conn:
            conn.sendall(b'CONNECT 127.0.0.1:443 HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n')
            assert b'403' in conn.recv(1024)
    finally:
        proxy.shutdown()
        proxy.server_close()
