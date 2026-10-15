import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from r0env import network


def test_real_http_proxy_and_direct(monkeypatch):
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            seen.append(self.path)
            body = json.dumps({'success': True, 'ip': '8.8.8.8'}).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setenv('no_proxy', '')
    monkeypatch.setenv('NO_PROXY', '')
    try:
        assert network.fetch_json('http://example.invalid/probe', url)['ip'] == '8.8.8.8'
        assert seen[-1] == 'http://example.invalid/probe'
        monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:1')
        monkeypatch.setenv('R0ENV_PROXY', 'http://127.0.0.1:1')
        assert network.fetch_json(url + '/direct', '')['success']
        assert seen[-1] == '/direct'
    finally:
        server.shutdown(); server.server_close(); thread.join()
