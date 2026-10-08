from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
port = int(os.environ.get("PORT", 8000))
HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler).serve_forever()
