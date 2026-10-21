"""Loopback-only workbench, with per-role bearer access and no outbound actions."""
from __future__ import annotations
import argparse
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import threading
from pathlib import Path
from .workbench import Workspace, MAX_UPLOAD

ASSETS = Path(__file__).with_name('workbench_ui')


class BoundedHTTPServer(ThreadingHTTPServer):
    """Bound idle sockets and worker threads for the private operator service."""
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, address, handler, *, max_connections=16, socket_timeout=10):
        self.slots = threading.BoundedSemaphore(max_connections)
        self.socket_timeout = socket_timeout
        super().__init__(address, handler)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(self.socket_timeout)
        return request, address

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def make_server(workspace, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, content, content_type='application/json'):
            raw = content if isinstance(content, bytes) else json.dumps(content).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(raw)

        def request_valid(self):
            for header in ('Host', 'Origin', 'Authorization', 'Content-Length', 'Content-Type'):
                if len(self.headers.get_all(header, [])) > 1:
                    raise PermissionError('ambiguous request headers')
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed:
                raise PermissionError('invalid loopback host')
            origin = self.headers.get('Origin')
            if origin and origin not in {'http://' + value for value in allowed}:
                raise PermissionError('cross-origin request rejected')

        def token(self):
            value = self.headers.get('Authorization', '')
            if not value.startswith('Bearer '):
                raise PermissionError('workspace credential required')
            return value[7:]

        def do_GET(self):
            try:
                self.request_valid()
                if self.path == '/api/state':
                    return self.reply(200, workspace.cases(self.token()))
                assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                          '/app.css': ('app.css', 'text/css; charset=utf-8')}
                if self.path not in assets:
                    return self.reply(404, {'error': 'not found'})
                name, kind = assets[self.path]
                self.reply(200, (ASSETS / name).read_bytes(), kind)
            except PermissionError as exc:
                self.reply(403, {'error': str(exc)})
            except Exception:
                self.reply(500, {'error': 'workspace unavailable; inspect private health report'})

        def do_POST(self):
            try:
                self.request_valid()
                token = self.token()
                workspace.principal(token)
                length = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or not 0 < length <= MAX_UPLOAD * 2:
                    raise ValueError('invalid request size')
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('JSON request required')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('incomplete request body')
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError('request must be an object')
                if self.path == '/api/upload':
                    result = workspace.upload(token, data['branch'], data['source'], data['content'], data.get('mapping'))
                elif self.path == '/api/preview':
                    content = data['content']
                    if not isinstance(content, str) or len(content.encode()) > MAX_UPLOAD:
                        raise ValueError('invalid preview size')
                    reader = csv.DictReader(io.StringIO(content), strict=True)
                    result = {'columns': reader.fieldnames or []}
                elif self.path == '/api/document':
                    result = workspace.upload_document(token, data['finding_id'], data['kind'], data['content'])
                elif self.path == '/api/review-document':
                    result = workspace.review_document(token, data['receipt_id'], data['expected_sha256'], data['note'])
                elif self.path == '/api/source':
                    result = workspace.read_source(token, data['receipt_id'])
                elif self.path == '/api/review':
                    result = workspace.review_source(token, data['branch'], data['source'], data['expected_sha256'], data['note'])
                elif self.path == '/api/settings':
                    workspace.configure(token, data['branch'], data['settings'])
                    result = {'saved': True}
                elif self.path == '/api/scan':
                    result = workspace.scan(token)
                elif self.path == '/api/action':
                    result = workspace.action(token, data['action'], data['finding_id'], data['expected_head'], data.get('data', {}))
                elif self.path == '/api/onboarding':
                    result = workspace.submit_onboarding(token, data['branch'], data['scope'])
                elif self.path == '/api/review-onboarding':
                    result = workspace.review_onboarding(token, data['branch'], data['expected_scope_hash'], data['note'])
                elif self.path == '/api/customer-delivery':
                    result = workspace.customer_delivery(token)
                elif self.path == '/api/backup':
                    result = workspace.backup(token)
                else:
                    return self.reply(404, {'error': 'not found'})
                self.reply(200, result)
            except PermissionError as exc:
                self.reply(403, {'error': str(exc)})
            except (ValueError, KeyError, TypeError, csv.Error) as exc:
                self.reply(400, {'error': str(exc)})
            except Exception:
                self.reply(500, {'error': 'operation failed; private workspace was not certified'})

    server = BoundedHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    server = make_server(Workspace(args.workspace), args.port)
    print(f'Open http://127.0.0.1:{server.server_port}; credentials remain in the private workspace.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
