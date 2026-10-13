"""Bounded local comparison to curl. Synthetic responses, no external network."""
import http.server
import json
import socketserver
import subprocess
import threading
import time

class Server(socketserver.TCPServer):
    allow_reuse_address = True

class Handler(http.server.BaseHTTPRequestHandler):
    hits = 0
    def log_message(self, *args):
        return
    def do_GET(self):
        Handler.hits += 1
        self.send_response(429 if Handler.hits == 1 else 200)
        if Handler.hits == 1:
            self.send_header('Retry-After','1')
        self.end_headers()
        self.wfile.write(b'' if Handler.hits == 1 else b'ok')

with Server(('127.0.0.1',0), Handler) as server:
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    start = time.monotonic()
    p = subprocess.run(['curl','--retry','1','--max-time','8','--silent','--show-error',
                        '--verbose',f'http://127.0.0.1:{server.server_address[1]}/'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,text=True,timeout=12)
    elapsed = round(time.monotonic()-start,3)
    server.shutdown()
    result = {'schema':'rma.dist.loopback-curl.v1','tool':'curl',
              'actual_local_binary':subprocess.check_output(['curl','--version'],text=True).splitlines()[0],
              'loopback_only':True,'synthetic_http_responses':True,
              'one_429_with_retry_after_seconds':1,'final_http_200':p.stdout=='ok',
              'requests_observed':Handler.hits,'return_code':p.returncode,
              'real_elapsed_seconds':elapsed,
              'observed_curl_retry_notice':'Will retry in 1 seconds' in p.stderr,
              'stderr_excerpt':[line.strip() for line in p.stderr.splitlines() if 'retry' in line.lower()][-5:],
              'customer_benchmark':False,'third_party_service_contacted':False}
    print(json.dumps(result,indent=2,sort_keys=True))
    if p.returncode!=0 or p.stdout!='ok' or Handler.hits!=2:
        raise SystemExit(1)
