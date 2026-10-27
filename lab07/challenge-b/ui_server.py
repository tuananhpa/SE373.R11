"""Loopback-only UI. One worker at a time; no shell or arbitrary-file HTTP endpoint."""
import argparse
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import app

def create_server(port=0, perform=None):
    perform = perform or app.perform
    jobs = {}
    lock = threading.Lock()
    busy = threading.Event()
    web = Path(__file__).parent / "web"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload, kind="application/json; charset=utf-8"):
            data = json.dumps(payload,ensure_ascii=True).encode() if "json" in kind else payload
            self.send_response(status)
            self.send_header("Content-Type",kind)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def local_request(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            host = self.headers.get("Host")
            origin = self.headers.get("Origin")
            if host != expected or origin not in (None,"http://" + expected):
                self.reply(403,{"error":"Chỉ chấp nhận địa chỉ loopback và origin của ứng dụng."})
                return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            url = urlsplit(self.path)
            if url.path == "/api/info":
                try:
                    self.reply(200,app.info())
                except Exception as exc:
                    self.reply(500,{"error":str(exc)})
            elif url.path in ("/api/status","/api/report"):
                key = parse_qs(url.query).get("id",[""])[0]
                with lock:
                    job = dict(jobs.get(key,{}))
                self.reply(200 if job else 404,job or {"error":"Không tìm thấy lượt chạy."})
            elif url.path in ("/","/app.js","/style.css"):
                name = "index.html" if url.path == "/" else url.path[1:]
                types = {"index.html":"text/html; charset=utf-8",
                         "app.js":"text/javascript; charset=utf-8","style.css":"text/css; charset=utf-8"}
                self.reply(200,(web/name).read_bytes(),types[name])
            else:
                self.reply(404,{"error":"Not found"})

        def do_POST(self):
            if not self.local_request():
                return
            if self.path != "/api/run":
                self.reply(404,{"error":"Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length","0"))
                if not 0 < length <= 16384 or "application/json" not in self.headers.get("Content-Type",""):
                    raise ValueError("Yêu cầu JSON, tối đa 16 KB.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload,dict):
                    raise ValueError("Payload phải là object.")
                if type(payload.get("live",False)) is not bool:
                    raise ValueError("live phải là boolean.")
            except (ValueError,UnicodeError) as exc:
                self.reply(400,{"error":str(exc)})
                return
            with lock:
                if busy.is_set():
                    self.reply(409,{"error":"Đang có lượt chạy. Đợi hoàn tất trước khi gửi tiếp."})
                    return
                busy.set()
                key = uuid.uuid4().hex
                if len(jobs) >= 30:
                    jobs.pop(next(iter(jobs)))
                jobs[key] = {"id":key,"status":"running"}
            def work():
                try:
                    result = perform(payload)
                    with lock:
                        jobs[key].update(status="completed",result=result)
                except Exception as exc:
                    with lock:
                        jobs[key].update(status="failed",error=str(exc))
                finally:
                    busy.clear()
            threading.Thread(target=work,daemon=True).start()
            self.reply(202,{"id":key,"status":"running"})

    return ThreadingHTTPServer(("127.0.0.1",port),Handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8766)
    args = parser.parse_args()
    server = create_server(args.port)
    print(f"Mở http://127.0.0.1:{server.server_port}",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
