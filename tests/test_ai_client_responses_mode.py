# coding=utf-8

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from trendradar.ai.client import AIClient


class AIClientResponsesModeTests(unittest.TestCase):
    @patch("trendradar.ai.client.requests.post")
    def test_chat_uses_responses_api_when_enabled(self, mock_post: Mock):
        mock_resp = Mock()
        mock_resp.json.return_value = {"output_text": "你好，我看见了一张图片。"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        client = AIClient(
            {
                "MODEL": "openai/doubao-seed-2-0-lite-260215",
                "API_KEY": "k-test",
                "API_BASE": "https://ark.cn-beijing.volces.com/api/v3",
                "API_MODE": "responses",
            }
        )
        content = client.chat([{"role": "user", "content": "你看见了什么？"}])

        self.assertEqual(content, "你好，我看见了一张图片。")
        self.assertTrue(mock_post.called, "responses mode should call HTTP /responses endpoint")
        url = mock_post.call_args.kwargs["url"]
        self.assertTrue(url.endswith("/responses"))
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "doubao-seed-2-0-lite-260215")
        self.assertEqual(payload["input"][0]["role"], "user")

    @patch("trendradar.ai.client.requests.post")
    def test_chat_parses_responses_output_blocks(self, mock_post: Mock):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "第一段。"},
                        {"type": "output_text", "text": "第二段。"},
                    ]
                }
            ]
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        client = AIClient(
            {
                "MODEL": "openai/doubao-seed-2-0-lite-260215",
                "API_KEY": "k-test",
                "API_BASE": "https://ark.cn-beijing.volces.com/api/v3",
                "API_MODE": "responses",
            }
        )
        content = client.chat([{"role": "user", "content": "总结"}])
        self.assertIn("第一段。", content)
        self.assertIn("第二段。", content)
