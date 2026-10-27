import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from ui_server import create_server

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.release = threading.Event()
        def perform(payload):
            self.release.wait(2)
            return {"passed":True}
        self.server = create_server(0,perform)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
    def tearDown(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
    def send(self, data, headers=None):
        return urlopen(Request(self.base+"/api/run",data=data,
            headers=headers or {"Content-Type":"application/json"}),timeout=4)
    def test_static_and_no_file_leak(self):
        with urlopen(self.base) as response:
            self.assertIn(b'<html lang="vi">',response.read())
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base+"/runtime.py")
        self.assertEqual(err.exception.code,404)
    def test_origin_and_bad_body(self):
        for data, headers, expected in [
            (b"{}",{"Content-Type":"application/json","Origin":"https://evil.example"},403),
            (b"[]",None,400), (b'{"live":"false"}',None,400)]:
            with self.assertRaises(HTTPError) as err:
                self.send(data,headers)
            self.assertEqual(err.exception.code,expected)
    def test_background_job_and_duplicate_guard(self):
        with self.send(b"{}") as response:
            job = json.load(response)
        with self.assertRaises(HTTPError) as err:
            self.send(b"{}")
        self.assertEqual(err.exception.code,409)
        with urlopen(self.base+"/api/status?id="+job["id"]) as response:
            self.assertEqual(json.load(response)["status"],"running")
        self.release.set()

if __name__ == "__main__":
    unittest.main()
