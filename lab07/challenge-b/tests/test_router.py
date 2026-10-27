import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch
from runtime import RouterModel, load_config, object_schema, text_schema

class RouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.received = []
        self.response = {"choices":[{"message":{"content":'{"answer":"OK"}'},"finish_reason":"stop"}],
                         "usage":{"prompt_tokens":25,"completion_tokens":7,
                                  "prompt_tokens_details":{"cached_tokens":10}}}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                owner.received.append((self.path,self.headers.get("Authorization"),
                                       json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                payload = json.dumps(owner.response).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(payload)
        self.server = HTTPServer(("127.0.0.1",0),Handler)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.config = {"OPENAI_API_KEY":"test-secret-do-not-log","OPENAI_MODEL":"cx/test",
                       "OPENAI_BASE_URL":f"http://127.0.0.1:{self.server.server_port}/v1"}

    def test_env_quotes_and_environment_precedence(self):
        path = self.root/".env"
        path.write_text('OPENAI_API_KEY="file-key"\nOPENAI_BASE_URL=http://localhost:20128/v1\nOPENAI_MODEL=cx/test\n',encoding="utf-8")
        with patch.dict("os.environ",{"OPENAI_API_KEY":"process-key"},clear=True):
            config = load_config(path)
        self.assertEqual(config["OPENAI_API_KEY"],"process-key")
        self.assertEqual(config["OPENAI_MODEL"],"cx/test")

    def test_request_usage_schema_and_no_key_artifacts(self):
        answer, usage = RouterModel(self.config)("Return OK",object_schema({"answer":text_schema()}),self.root/"step")
        self.assertEqual(answer,{"answer":"OK"})
        self.assertEqual(usage,{"input_tokens":25,"cached_input_tokens":10,"output_tokens":7})
        path,auth,body = self.received[0]
        self.assertEqual(path,"/v1/chat/completions")
        self.assertEqual(auth,"Bearer test-secret-do-not-log")
        self.assertEqual(body["model"],"cx/test")
        self.assertFalse(body["stream"])
        for file in self.root.iterdir():
            self.assertNotIn(self.config["OPENAI_API_KEY"],file.read_text(encoding="utf-8"))

    def test_missing_usage_and_invalid_action_fail_without_retry(self):
        for response in [
            {"choices":[{"message":{"content":'{"answer":"OK"}'},"finish_reason":"stop"}]},
            {"choices":[{"message":{"content":'{"answer":1}'},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1}},
            {"choices":[{"message":{"content":'{"answer":"OK"}'},"finish_reason":"length"}],"usage":{"prompt_tokens":1,"completion_tokens":1}},
        ]:
            self.response = response
            before = len(self.received)
            with self.assertRaises((ValueError,RuntimeError)):
                RouterModel(self.config)("test",object_schema({"answer":text_schema()}),self.root/"bad")
            self.assertEqual(len(self.received),before+1)

    def test_refuse_unsafe_url_or_missing_key(self):
        for change in ({"OPENAI_API_KEY":""},{"OPENAI_BASE_URL":"http://remote.example/v1"},
                       {"OPENAI_BASE_URL":"https://user:password@example.com/v1"}):
            with self.assertRaises(ValueError):
                RouterModel({**self.config,**change})("test",object_schema({"answer":text_schema()}),self.root/"bad")

if __name__ == "__main__":
    unittest.main()
