# coding=utf-8

from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path
from typing import Dict, List
from wsgiref.util import setup_testing_defaults


def _load_entry_module():
    path = Path(__file__).resolve().parents[1] / "api" / "index.py"
    spec = importlib.util.spec_from_file_location("day_vibe_api_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _invoke_wsgi(app, path: str) -> Dict[str, object]:
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = "GET"
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = ""
    environ["wsgi.input"] = io.BytesIO(b"")
    environ["CONTENT_LENGTH"] = "0"

    status_headers: Dict[str, object] = {}

    def _start_response(status: str, headers: List[tuple[str, str]]):
        status_headers["status"] = status
        status_headers["headers"] = headers

    body_chunks = app(environ, _start_response)
    body = b"".join(body_chunks)
    return {
        "status": status_headers.get("status", ""),
        "headers": status_headers.get("headers", []),
        "body": body,
    }


class VercelEntrypointTests(unittest.TestCase):
    def test_vercel_entrypoint_exposes_wsgi_callable_app_and_health_endpoint(self):
        module = _load_entry_module()
        self.assertTrue(hasattr(module, "app"), "api/index.py must expose top-level app")
        self.assertTrue(callable(module.app), "top-level app must be callable")

        result = _invoke_wsgi(module.app, "/api/health")
        self.assertTrue(str(result["status"]).startswith("200"))
        payload = json.loads(result["body"].decode("utf-8"))
        self.assertIs(payload["ok"], True)
