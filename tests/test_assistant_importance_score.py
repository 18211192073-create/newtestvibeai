import unittest

from trendradar.assistant.digest import _compute_editorial_importance


class AssistantImportanceScoreTests(unittest.TestCase):
    def test_authoritative_frontier_news_scores_higher_than_hotlist_noise(self) -> None:
        serious = _compute_editorial_importance(
            title="OpenAI 发布新一代推理模型并开放开发者 API",
            source_name="OpenAI News",
            source_id="openai-news",
            source_type="rss",
            rank=18,
        )
        noise = _compute_editorial_importance(
            title="AI染指鬼灭,日网友气急跳脚",
            source_name="贴吧",
            source_id="tieba",
            source_type="hotlist",
            rank=1,
        )
        self.assertGreater(serious, noise)

    def test_grok_and_gemini_frontier_topics_get_high_score(self) -> None:
        grok_news = _compute_editorial_importance(
            title="xAI Grok 发布代码智能体并接入 GitHub 工作流",
            source_name="xAI Blog",
            source_id="grok-news",
            source_type="rss",
            rank=25,
        )
        gemini_news = _compute_editorial_importance(
            title="Google Gemini 推出企业级 Agent Skills 编排能力",
            source_name="Google Blog",
            source_id="google-blog",
            source_type="rss",
            rank=30,
        )
        self.assertGreaterEqual(grok_news, 75)
        self.assertGreaterEqual(gemini_news, 75)

    def test_sensational_words_are_penalized(self) -> None:
        plain = _compute_editorial_importance(
            title="Anthropic 发布新模型并更新 API 文档",
            source_name="Anthropic News",
            source_id="anthropic-news",
            source_type="rss",
            rank=40,
        )
        sensational = _compute_editorial_importance(
            title="Anthropic 新模型引爆全网炸锅怒怼",
            source_name="贴吧",
            source_id="tieba",
            source_type="hotlist",
            rank=3,
        )
        self.assertGreater(plain, sensational)


if __name__ == "__main__":
    unittest.main()
