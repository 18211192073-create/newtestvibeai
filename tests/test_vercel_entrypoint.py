# coding=utf-8

from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from wsgiref.util import setup_testing_defaults


def _load_entry_module():
    path = Path(__file__).resolve().parents[1] / "api" / "index.py"
    spec = importlib.util.spec_from_file_location("day_vibe_api_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _invoke_wsgi(
    app,
    path: str,
    method: str = "GET",
    query_string: str = "",
    payload: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query_string
    raw_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else b""
    environ["wsgi.input"] = io.BytesIO(raw_payload)
    environ["CONTENT_LENGTH"] = str(len(raw_payload))
    if raw_payload:
        environ["CONTENT_TYPE"] = "application/json"

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
    def test_vercel_entrypoint_exports_aliases_callable(self):
        module = _load_entry_module()
        for export_name in ("app", "application", "handler"):
            self.assertTrue(hasattr(module, export_name), f"missing export: {export_name}")
            self.assertTrue(callable(getattr(module, export_name)), f"{export_name} must be callable")

    def test_vercel_entrypoint_exposes_wsgi_callable_app_and_health_endpoint(self):
        module = _load_entry_module()
        self.assertTrue(hasattr(module, "app"), "api/index.py must expose top-level app")
        self.assertTrue(callable(module.app), "top-level app must be callable")

        result = _invoke_wsgi(module.app, "/api/health")
        self.assertTrue(str(result["status"]).startswith("200"))
        payload = json.loads(result["body"].decode("utf-8"))
        self.assertIs(payload["ok"], True)

    def test_latest_endpoint_and_bookmark_validation(self):
        module = _load_entry_module()
        latest = _invoke_wsgi(module.app, "/api/latest")
        self.assertTrue(str(latest["status"]).startswith("200"))
        latest_payload = json.loads(latest["body"].decode("utf-8"))
        self.assertIs(latest_payload["ok"], True)
        self.assertIn("report", latest_payload)

        missing_item = _invoke_wsgi(module.app, "/api/bookmarks", method="POST", payload={"note": "x"})
        self.assertTrue(str(missing_item["status"]).startswith("400"))
        missing_payload = json.loads(missing_item["body"].decode("utf-8"))
        self.assertIs(missing_payload["ok"], False)

    def test_module_uses_lazy_runtime_init(self):
        module = _load_entry_module()
        self.assertIsNone(getattr(module, "_storage", None))
        self.assertIsNone(getattr(module, "_assistant_settings", None))

        result = _invoke_wsgi(module.app, "/api/health")
        self.assertTrue(str(result["status"]).startswith("200"))
        self.assertIsNotNone(getattr(module, "_storage", None))
        self.assertIsNotNone(getattr(module, "_assistant_settings", None))
