"""Docker lifecycle test, run after docker build -t transcribe-ai:test ."""
import base64
import json
import secrets
import subprocess
import time
import urllib.request
import uuid


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    name = 'transcribe-test-' + uuid.uuid4().hex[:8]
    volume = name + '-data'
    password = secrets.token_urlsafe(24)
    auth = base64.b64encode(f'admin:{password}'.encode()).decode()
    docker('volume', 'create', volume)
    try:
        docker('run', '-d', '--name', name, '-p', '127.0.0.1::8000',
               '-e', 'APP_PASSWORD=' + password, '-v', volume + ':/data', 'transcribe-ai:test')
        binding = json.loads(docker('inspect', name))[0]['NetworkSettings']['Ports']['8000/tcp'][0]
        origin = 'http://127.0.0.1:' + binding['HostPort']
        for _ in range(60):
            try:
                urllib.request.urlopen(origin + '/healthz', timeout=2)
                break
            except OSError:
                time.sleep(1)
        else:
            raise AssertionError('Container never became healthy')
        request = urllib.request.Request(origin + '/', headers={'Authorization': 'Basic ' + auth})
        assert b'Transcribe' in urllib.request.urlopen(request).read()
        # Seed completed result without downloading a model. Check persistence through real restart.
        id = 'a' * 32
        code = "from pathlib import Path; import store; Path('/data/jobs/" + id + "').mkdir(); store.enqueue('" + id + "','fixture.wav','ca',''); store.update('" + id + "',status='done',text='Bon dia',detected='ca')"
        docker('exec', name, 'python', '-c', code)
        docker('restart', name)
        for _ in range(30):
            try:
                request = urllib.request.Request(origin + '/api/jobs/' + id, headers={'Authorization': 'Basic ' + auth})
                assert json.loads(urllib.request.urlopen(request, timeout=2).read())['text'] == 'Bon dia'
                break
            except OSError:
                time.sleep(1)
        else:
            raise AssertionError('Restart check failed')
        request = urllib.request.Request(origin + '/api/jobs/' + id + '/word',
            data=json.dumps({'text': 'Text editat'}).encode(),
            headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
        assert urllib.request.urlopen(request).read().startswith(b'PK')
        print('Docker HTTP/auth/Word/persistence restart: passed')
    finally:
        subprocess.run(['docker', 'rm', '-f', name], check=False, capture_output=True)
        subprocess.run(['docker', 'volume', 'rm', volume], check=False, capture_output=True)


if __name__ == '__main__':
    main()
