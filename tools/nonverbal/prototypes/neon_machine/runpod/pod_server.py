"""A tiny file-and-job server for a rented GPU Pod, reached through Runpod's HTTPS proxy
(https://<pod-id>-8000.proxy.runpod.net), so a sandbox that only speaks HTTPS can drive the render.

Started by the Pod's start command (see README.md); standard library only. Every request must carry the
header X-Token: <POD_TOKEN>, a random string passed to the Pod as an environment variable.

  GET  /ping                 -> ok
  PUT  /f/<path>             upload a file to /work/<path> (parent folders are made)
  GET  /f/<path>             download /work/<path>
  GET  /ls?d=<dir>           list /work/<dir> (name, size)
  POST /run                  body = a bash script; runs it in the background, output to /work/run.log
  GET  /log?n=<lines>        the last n lines of /work/run.log
  GET  /status               {"running": true|false, "rc": <exit code of the last run or null>}
"""
import json
import os
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

WORK = Path('/work')
WORK.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get('POD_TOKEN', '')
JOB = {'proc': None}


def safe(rel):
    p = (WORK / unquote(rel)).resolve()
    if WORK.resolve() not in p.parents and p != WORK.resolve():
        raise ValueError('outside /work')
    return p


class H(BaseHTTPRequestHandler):
    def _ok(self):
        if not TOKEN or self.headers.get('X-Token') != TOKEN:
            self.send_error(403)
            return False
        return True

    def _send(self, code, body, ctype='text/plain'):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._ok():
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == '/ping':
            return self._send(200, 'ok')
        if u.path.startswith('/f/'):
            p = safe(u.path[3:])
            if not p.is_file():
                return self.send_error(404)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(p.stat().st_size))
            self.end_headers()
            with open(p, 'rb') as f:
                shutil.copyfileobj(f, self.wfile, 1 << 20)
            return
        if u.path == '/ls':
            d = safe(q.get('d', [''])[0])
            items = [(c.name, c.stat().st_size) for c in sorted(d.iterdir())] if d.is_dir() else []
            return self._send(200, json.dumps(items), 'application/json')
        if u.path == '/log':
            n = int(q.get('n', ['60'])[0])
            log = WORK / 'run.log'
            lines = log.read_text(errors='replace').splitlines()[-n:] if log.exists() else []
            return self._send(200, '\n'.join(lines))
        if u.path == '/status':
            p = JOB['proc']
            running = p is not None and p.poll() is None
            return self._send(200, json.dumps({'running': running, 'rc': None if p is None or running else p.returncode}),
                              'application/json')
        self.send_error(404)

    def do_PUT(self):
        if not self._ok():
            return
        u = urlparse(self.path)
        if not u.path.startswith('/f/'):
            return self.send_error(404)
        p = safe(u.path[3:])
        p.parent.mkdir(parents=True, exist_ok=True)
        n = int(self.headers.get('Content-Length', '0'))
        with open(p, 'wb') as f:
            while n > 0:
                chunk = self.rfile.read(min(n, 1 << 20))
                if not chunk:
                    break
                f.write(chunk)
                n -= len(chunk)
        self._send(200, f'{p.stat().st_size}')

    def do_POST(self):
        if not self._ok():
            return
        if urlparse(self.path).path != '/run':
            return self.send_error(404)
        if JOB['proc'] is not None and JOB['proc'].poll() is None:
            return self._send(409, 'a job is running')
        script = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        (WORK / 'job.sh').write_bytes(script)
        log = open(WORK / 'run.log', 'ab')
        JOB['proc'] = subprocess.Popen(['bash', str(WORK / 'job.sh')], cwd=WORK, stdout=log, stderr=subprocess.STDOUT)
        self._send(200, 'started')

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8000), H).serve_forever()
