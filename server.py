import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(ROOT, "index.html")


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        if self.path.split("?", 1)[0] != "/proxy":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/proxy":
            self.handle_proxy("GET")
            return
        self.handle_index()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/proxy":
            self.send_response(404)
            self.end_headers()
            return
        self.handle_proxy("POST")

    def handle_index(self):
        try:
            with open(INDEX_PATH, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def handle_proxy(self, method):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        target = q.get("url", [None])[0]
        if not target:
            self.send_response(400)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Missing url")
            return

        headers = {"Accept": self.headers.get("Accept", "application/json")}
        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth

        body = None
        if method == "POST":
            length = self.headers.get("Content-Length")
            if length:
                try:
                    body = self.rfile.read(int(length))
                except Exception:
                    body = None
            ctype = self.headers.get("Content-Type")
            if ctype:
                headers["Content-Type"] = ctype

        req = urllib.request.Request(target, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                code = resp.getcode()
                ctype = resp.headers.get("Content-Type", "application/json")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            ctype = e.headers.get("Content-Type", "text/plain; charset=utf-8") if e.headers else "text/plain; charset=utf-8"
            self.send_header("Content-Type", ctype)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                data = e.read()
                if data:
                    self.wfile.write(data)
            except Exception:
                pass
        except Exception:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"Bad Gateway")


def run():
    server = HTTPServer(("0.0.0.0", 8089), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
