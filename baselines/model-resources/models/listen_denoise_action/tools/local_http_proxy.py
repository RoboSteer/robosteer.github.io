#!/usr/bin/env python3
"""Small localhost-only HTTP CONNECT proxy for an SSH reverse tunnel."""
import http.client
import http.server
import socket
import socketserver
import threading
from urllib.parse import urlsplit


def relay(left, right):
    # Keep both directions flowing concurrently.  A single non-blocking
    # selector loop can drop large wheels when sendall() hits backpressure.
    def pump(source, destination):
        try:
            while True:
                data = source.recv(1024 * 256)
                if not data:
                    break
                destination.sendall(data)
        finally:
            try:
                destination.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    threads = [
        threading.Thread(target=pump, args=(left, right), daemon=True),
        threading.Thread(target=pump, args=(right, left), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_CONNECT(self):
        host, port_text = self.path.rsplit(":", 1)
        upstream = socket.create_connection((host, int(port_text)), timeout=30)
        try:
            self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.wfile.flush()
            relay(self.connection, upstream)
        finally:
            upstream.close()

    def do_GET(self):
        self.forward_http()

    do_HEAD = do_GET
    do_POST = do_GET

    def forward_http(self):
        parsed = urlsplit(self.path)
        if not parsed.hostname:
            self.send_error(400, "absolute URL required")
            return
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection = http.client.HTTPConnection(parsed.hostname, port, timeout=60)
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"proxy-connection", "connection", "keep-alive"}
        }
        connection.request(self.command, path, headers=headers)
        response = connection.getresponse()
        self.send_response(response.status, response.reason)
        for key, value in response.getheaders():
            if key.lower() not in {"connection", "transfer-encoding"}:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.read())
        connection.close()


class ThreadingProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


with ThreadingProxy(("127.0.0.1", 8888), ProxyHandler) as server:
    server.serve_forever()
