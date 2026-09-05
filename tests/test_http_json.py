# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.http_json import request_json  # noqa: E402


class FakeUrlResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class HttpJsonTests(unittest.TestCase):
    def test_stdlib_fallback_handles_missing_requests(self):
        with patch("multitude.http_json._load_requests", return_value=None):
            with patch("multitude.http_json.urllib_request.urlopen", return_value=FakeUrlResponse({"ok": True}, 200)):
                status, data = request_json("GET", "https://example.test/api", timeout=1)
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})


if __name__ == "__main__":
    unittest.main()
