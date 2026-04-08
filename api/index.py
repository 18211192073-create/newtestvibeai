"""Vercel WSGI entrypoint for DAY VIBE AI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import parse_qs

from trendradar.assistant.digest import build_daily_digest, build_reading_log_draft, load_assistant_settings, render_report_html
from trendradar.assistant.storage import AssistantStorage

_storage = AssistantStorage()
_assistant_settings = load_assistant_settings()


def _json_response(payload: Dict[str, Any], status: str = "200 OK") -> Tuple[str, List[Tuple[str, str]], bytes]:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    return status, headers, body


def _html_response(html: str, status: str = "200 OK") -> Tuple[str, List[Tuple[str, str]], bytes]:
    body = html.encode("utf-8")
    headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    return status, headers, body


def _read_json_body(environ: Dict[str, Any]) -> Dict[str, Any]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except (ValueError, TypeError):
        length = 0
    raw = environ["wsgi.input"].read(length) if length > 0 else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _ensure_latest_report() -> Dict[str, Any]:
    report = _storage.get_latest_report()
    if not report:
        report = build_daily_digest(assistant_settings=_assistant_settings, storage=_storage)
    report["bookmarks"] = _storage.list_bookmarks()
    report["logs"] = _storage.list_reading_logs()
    return report


def _find_item_in_report(item_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
    for report_item in report.get("items", []):
        if report_item.get("item_id") == item_id:
            return dict(report_item)
    for bookmark in report.get("bookmarks", []):
        if bookmark.get("item_id") == item_id:
            return {
                "item_id": bookmark.get("item_id", ""),
                "report_id": bookmark.get("report_id", report.get("report_id", "")),
                "title": bookmark.get("title", ""),
                "summary": bookmark.get("summary", ""),
                "source_name": bookmark.get("source_name", ""),
                "source_url": bookmark.get("source_url", ""),
                "image_url": bookmark.get("image_url", ""),
                "importance": bookmark.get("importance", 0),
                "note": bookmark.get("note", ""),
            }
    return {}


def app(environ: Dict[str, Any], start_response) -> Iterable[bytes]:
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    path = environ.get("PATH_INFO", "/") or "/"
    query = parse_qs(environ.get("QUERY_STRING", ""))

    status = "404 Not Found"
    headers: List[Tuple[str, str]]
    body = b""

    if method == "GET":
        if path in {"/", "/index.html"}:
            report = _ensure_latest_report()
            status, headers, body = _html_response(render_report_html(report))
        elif path == "/api/health":
            status, headers, body = _json_response({"ok": True})
        elif path == "/api/latest":
            status, headers, body = _json_response({"ok": True, "report": _ensure_latest_report()})
        elif path == "/api/reports":
            status, headers, body = _json_response({"ok": True, "reports": _storage.list_reports()})
        elif path == "/api/bookmarks":
            status, headers, body = _json_response({"ok": True, "bookmarks": _storage.list_bookmarks()})
        elif path == "/api/logs":
            item_id = (query.get("item_id") or [None])[0]
            status, headers, body = _json_response({"ok": True, "logs": _storage.list_reading_logs(item_id=item_id)})
        elif path == "/api/item":
            item_id = (query.get("item_id") or [None])[0]
            if not item_id:
                status, headers, body = _json_response({"ok": False, "error": "missing item_id"}, status="400 Bad Request")
            else:
                report = _ensure_latest_report()
                item = _find_item_in_report(item_id, report)
                if not item:
                    status, headers, body = _json_response({"ok": False, "error": "item not found"}, status="404 Not Found")
                else:
                    status, headers, body = _json_response(
                        {
                            "ok": True,
                            "item": item,
                            "bookmark": _storage.get_bookmark(item_id),
                            "logs": _storage.list_reading_logs(item_id=item_id),
                        }
                    )
        elif path == "/api/generate":
            report = build_daily_digest(assistant_settings=_assistant_settings, storage=_storage)
            status, headers, body = _json_response({"ok": True, "report": report})
        elif path == "/latest-report.html":
            report_path = _storage.data_dir / "latest-report.html"
            if report_path.exists():
                status, headers, body = _html_response(report_path.read_text(encoding="utf-8"))
            else:
                status, headers, body = _json_response({"ok": False, "error": "not found"}, status="404 Not Found")
        else:
            status, headers, body = _json_response({"ok": False, "error": "not found"}, status="404 Not Found")

    elif method == "POST":
        payload = _read_json_body(environ)
        if path == "/api/refresh":
            started_at = time.time()
            try:
                from mcp_server.tools.system import SystemManagementTools

                project_root = str(Path(__file__).resolve().parents[1])
                crawl_result = SystemManagementTools(project_root=project_root).trigger_crawl(
                    save_to_local=True,
                    include_url=False,
                )
            except Exception as exc:
                status, headers, body = _json_response({"ok": False, "error": f"抓取失败: {exc}"}, status="500 Internal Server Error")
            else:
                report = build_daily_digest(assistant_settings=_assistant_settings, storage=_storage)
                elapsed_seconds = max(1, round(time.time() - started_at))
                status, headers, body = _json_response(
                    {"ok": True, "crawl": crawl_result, "report": report, "elapsed_seconds": elapsed_seconds}
                )
        elif path == "/api/bookmarks":
            item_id = payload.get("item_id")
            title = payload.get("title", "")
            report_id = payload.get("report_id", "")
            note = payload.get("note", "")
            bookmarked = payload.get("bookmarked")
            if isinstance(bookmarked, str):
                bookmarked = bookmarked.strip().lower() in {"1", "true", "yes", "on"}

            report = _ensure_latest_report()
            item = _find_item_in_report(item_id, report)
            if item_id and not item:
                item = {"item_id": item_id, "report_id": report_id or report.get("report_id", ""), "title": title or item_id}
            if not item:
                status, headers, body = _json_response({"ok": False, "error": "missing item_id"}, status="400 Bad Request")
            else:
                item["report_id"] = report_id or report.get("report_id", "")
                item["title"] = title or item.get("title", "")
                if bookmarked is False:
                    result = _storage.remove_bookmark(item["item_id"])
                elif bookmarked is True:
                    result = _storage.set_bookmark(item, note=note)
                else:
                    existing = _storage.get_bookmark(item["item_id"])
                    result = _storage.remove_bookmark(item["item_id"]) if existing else _storage.set_bookmark(item, note=note)
                status, headers, body = _json_response({"ok": True, **result})
        elif path == "/api/logs":
            item_id = payload.get("item_id")
            log_text = (payload.get("log_text") or "").strip()
            draft_text = (payload.get("draft_text") or "").strip()
            log_title = (payload.get("log_title") or payload.get("title") or "").strip()
            if not item_id or not log_text:
                status, headers, body = _json_response(
                    {"ok": False, "error": "item_id 和 log_text 不能为空"},
                    status="400 Bad Request",
                )
            else:
                report = _ensure_latest_report()
                item = _find_item_in_report(item_id, report) or {
                    "item_id": item_id,
                    "report_id": report.get("report_id", ""),
                    "title": payload.get("title", ""),
                }
                item["report_id"] = report.get("report_id", "")
                item["draft_text"] = draft_text
                item["draft_title"] = log_title
                status, headers, body = _json_response({"ok": True, **_storage.add_reading_log(item, log_text, log_title=log_title)})
        elif path == "/api/log-draft":
            item_id = payload.get("item_id")
            if not item_id:
                status, headers, body = _json_response({"ok": False, "error": "missing item_id"}, status="400 Bad Request")
            else:
                report = _ensure_latest_report()
                item = _find_item_in_report(item_id, report)
                if not item:
                    status, headers, body = _json_response({"ok": False, "error": "item not found"}, status="404 Not Found")
                else:
                    draft = build_reading_log_draft(
                        item=item,
                        report=report,
                        existing_logs=_storage.list_reading_logs(item_id=item_id),
                        assistant_settings=_assistant_settings,
                    )
                    status, headers, body = _json_response({"ok": True, "draft": draft})
        elif path == "/api/generate":
            report = build_daily_digest(assistant_settings=_assistant_settings, storage=_storage)
            status, headers, body = _json_response({"ok": True, "report": report})
        else:
            status, headers, body = _json_response({"ok": False, "error": "not found"}, status="404 Not Found")
    else:
        status, headers, body = _json_response({"ok": False, "error": "method not allowed"}, status="405 Method Not Allowed")

    start_response(status, headers)
    return [body]


application = app
handler = app
