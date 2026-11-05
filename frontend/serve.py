import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 5500


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


os.chdir(Path(__file__).resolve().parent)
print(f"http://127.0.0.1:{PORT}")
ThreadingHTTPServer(("127.0.0.1", PORT), NoCacheHandler).serve_forever()
