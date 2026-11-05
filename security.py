"""Canonical YouTube IDs only; outbound HTTPS tunnel pins a public IP per connection."""
import http.server
import ipaddress
import re
import select
import socket
import socketserver
import threading
from urllib.parse import urlsplit, parse_qs


def youtube_url(value):
    try:
        u = urlsplit(value)
        if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or u.fragment:
            raise ValueError
        if u.hostname == 'youtu.be':
            video = u.path.removeprefix('/')
        elif u.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
            if u.path == '/watch':
                video = parse_qs(u.query).get('v', [''])[0]
            elif re.fullmatch(r'/(shorts|embed)/[A-Za-z0-9_-]{11}', u.path):
                video = u.path.split('/')[-1]
            else:
                raise ValueError
        else:
            raise ValueError
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
            raise ValueError
        return 'https://www.youtube.com/watch?v=' + video
    except (ValueError, TypeError):
        raise ValueError('Usa un enlace HTTPS de un vídeo de YouTube, sin listas ni otros destinos.') from None


def allowed_host(host):
    return any(host == root or host.endswith('.' + root)
               for root in ('youtube.com', 'googlevideo.com', 'ytimg.com', 'youtube-nocookie.com'))


def public_addresses(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Destino no público')
    return addresses


class Tunnel(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_CONNECT(self):
        try:
            host, port = self.path.rsplit(':', 1)
            if port != '443' or not allowed_host(host):
                raise ValueError('Destino no permitido')
            addresses = public_addresses(host, 443)
            upstream = None
            for family, kind, proto, _, address in addresses:
                candidate = socket.socket(family, kind, proto)
                candidate.settimeout(15)
                try:
                    candidate.connect(address)  # Connect to validated numeric address; no DNS re-resolution.
                    upstream = candidate
                    break
                except OSError:
                    candidate.close()
            if upstream is None:
                raise OSError('Sin conexión')
        except (OSError, ValueError):
            self.send_error(403)
            return
        with upstream:
            self.send_response(200, 'Connection established')
            self.end_headers()
            self.connection.settimeout(30)
            while True:
                ready, _, _ = select.select([self.connection, upstream], [], [], 30)
                if not ready:
                    break
                for source in ready:
                    try:
                        data = source.recv(65536)
                        if not data:
                            return
                        (upstream if source is self.connection else self.connection).sendall(data)
                    except OSError:
                        return


class Proxy(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def start_proxy():
    server = Proxy(('127.0.0.1', 0), Tunnel)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
