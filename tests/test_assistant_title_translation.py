import unittest

from trendradar.assistant.digest import (
    _ensure_chinese_display_titles,
    _is_likely_english_title,
)


class AssistantTitleTranslationTests(unittest.TestCase):
    def test_detects_likely_english_title(self) -> None:
        self.assertTrue(_is_likely_english_title("OpenAI launches new coding agent for GitHub"))
        self.assertFalse(_is_likely_english_title("OpenAI 发布新的编程智能体"))
        self.assertFalse(_is_likely_english_title(""))

    def test_english_titles_are_forced_to_chinese_display_title(self) -> None:
        items = [
            {
                "item_id": "a1",
                "title": "OpenAI launches new coding agent for GitHub",
                "display_title": "OpenAI launches new coding agent for GitHub",
                "original_title": "OpenAI launches new coding agent for GitHub",
            },
            {
                "item_id": "a2",
                "title": "Gemini adds skills orchestration for enterprise agents",
                "display_title": "Gemini adds skills orchestration for enterprise agents",
                "original_title": "Gemini adds skills orchestration for enterprise agents",
            },
        ]

        settings = {"ai": {"api_key_env": "NON_EXISTING_ENV_FOR_TEST"}}
        translated = _ensure_chinese_display_titles(items, assistant_settings=settings)

        self.assertEqual(len(translated), 2)
        for item in translated:
            display_title = item.get("display_title", "")
            self.assertTrue(any("\u4e00" <= ch <= "\u9fff" for ch in display_title), display_title)

    def test_chinese_title_keeps_original_display(self) -> None:
        items = [
            {
                "item_id": "b1",
                "title": "OpenAI 发布新模型",
                "display_title": "OpenAI 发布新模型",
                "original_title": "OpenAI 发布新模型",
            }
        ]
        settings = {"ai": {"api_key_env": "NON_EXISTING_ENV_FOR_TEST"}}
        translated = _ensure_chinese_display_titles(items, assistant_settings=settings)
        self.assertEqual(translated[0]["display_title"], "OpenAI 发布新模型")


if __name__ == "__main__":
    unittest.main()
