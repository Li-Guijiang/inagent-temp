import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "factory-console"))
import app  # noqa: E402


class FactoryConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.create_server(0, str(ROOT / "tests" / "runtime-data"))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get(self, path):
        with urlopen(self.base + path, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def post(self, path, payload):
        request = Request(
            self.base + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health(self):
        status, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_process_parser_and_validation(self):
        status, body = self.post("/api/agent/parse-process", {"doc_text": "焊接电流：180 A\n电流范围 170~190"})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(body["param_count"], 2)
        with self.assertRaises(HTTPError) as error:
            self.post("/api/agent/parse-process", {"doc_text": "无参数"})
        self.assertEqual(error.exception.code, 400)

    def test_report_validation(self):
        with self.assertRaises(HTTPError) as error:
            self.post("/api/quality/report", {"line": "1号线", "batch": "B1", "result": "未知"})
        self.assertEqual(error.exception.code, 400)
        status, body = self.post("/api/quality/report", {"line": "1号线", "batch": "B1", "result": "合格"})
        self.assertEqual(status, 200)
        self.assertTrue(body["record"]["id"])


if __name__ == "__main__":
    unittest.main()
