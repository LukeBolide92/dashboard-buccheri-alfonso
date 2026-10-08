from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(302)
            self.send_header('Location', '/static/index.html')
            self.end_headers()
            return
        super().do_GET()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[DEBUG] Serve statico avviato su 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
