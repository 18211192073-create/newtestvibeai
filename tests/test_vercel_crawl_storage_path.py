# coding=utf-8

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from mcp_server.tools.system import SystemManagementTools
from trendradar.assistant.digest import collect_candidates


class VercelCrawlStoragePathTests(unittest.TestCase):
    def test_collect_candidates_reads_from_day_vibe_crawl_dir(self):
        marker = "ZZZ_TEST_DAYVIBE_AI_ITEM"
        with tempfile.TemporaryDirectory() as tmpdir:
            news_dir = os.path.join(tmpdir, "news")
            os.makedirs(news_dir, exist_ok=True)
            db_path = os.path.join(news_dir, "2099-01-01.db")

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE platforms (id TEXT PRIMARY KEY, name TEXT)")
                conn.execute(
                    """
                    CREATE TABLE news_items (
                        title TEXT,
                        url TEXT,
                        mobile_url TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        first_crawl_time TEXT,
                        last_crawl_time TEXT,
                        rank INTEGER,
                        platform_id TEXT
                    )
                    """
                )
                conn.execute("INSERT INTO platforms (id, name) VALUES (?, ?)", ("p-test", "OpenAI Blog"))
                conn.execute(
                    """
                    INSERT INTO news_items
                    (title, url, mobile_url, created_at, updated_at, first_crawl_time, last_crawl_time, rank, platform_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (f"OpenAI Agent SDK {marker} 发布", "https://example.com/a", "", now_str, now_str, now_str, now_str, 1, "p-test"),
                )
                conn.commit()

            with patch.dict(os.environ, {"DAY_VIBE_CRAWL_DIR": tmpdir}, clear=False):
                candidates = collect_candidates(lookback_hours=48)
                self.assertTrue(
                    any(marker in item.title for item in candidates),
                    "collect_candidates should read SQLite files from DAY_VIBE_CRAWL_DIR",
                )

    def test_system_tool_resolves_tmp_dir_on_vercel(self):
        tools = SystemManagementTools(project_root="/tmp/day-vibe-path-test")
        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
            resolved = tools._resolve_crawl_data_dir()
        self.assertEqual(str(resolved), "/tmp/day-vibe-ai/output")

