import socket
import ssl
import sys

host = sys.argv[1] if len(sys.argv) > 1 else "github.com"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
with socket.create_connection((host, 443), timeout=30) as s:
    with ctx.wrap_socket(s, server_hostname=host) as ss:
        der = ss.getpeercert(True)
        print(ssl.DER_cert_to_PEM_cert(der))
