import unittest

from trendradar.assistant.digest import (
    DigestCandidate,
    _apply_source_mix,
    _categorize_source_kind,
    _compute_mix_targets,
    _is_ai_related,
    _source_mix_config,
    _source_priority_boost,
)


def _candidate(item_id: str, source_type: str, source_name: str, source_id: str, importance: float) -> DigestCandidate:
    return DigestCandidate(
        item_id=item_id,
        source_type=source_type,
        source_name=source_name,
        title=f"title-{item_id}",
        original_title=f"title-{item_id}",
        summary=f"summary-{item_id}",
        source_url=f"https://example.com/{item_id}",
        image_url="",
        published_at="2026-04-07 16:00:00",
        importance_hint=importance,
        raw={"source_id": source_id},
    )


class SourceMixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = {
            "source_mix": {
                "enabled": True,
                "english_authority": 0.55,
                "chinese_ai_tech": 0.30,
                "hotlist_trend": 0.15,
            }
        }

    def test_compute_mix_targets_for_eight(self) -> None:
        mix_cfg = _source_mix_config(self.settings)
        targets = _compute_mix_targets(8, mix_cfg)
        self.assertEqual(targets["english_authority"], 5)
        self.assertEqual(targets["chinese_ai_tech"], 2)
        self.assertEqual(targets["hotlist_trend"], 1)

    def test_apply_source_mix_prefers_balanced_buckets(self) -> None:
        candidates = []
        candidates.extend(
            [
                _candidate("en1", "rss", "OpenAI News", "openai-news", 100),
                _candidate("en2", "rss", "Anthropic News", "anthropic-news", 99),
                _candidate("en3", "rss", "Google DeepMind", "deepmind-blog", 98),
                _candidate("en4", "rss", "The Verge", "the-verge", 97),
                _candidate("en5", "rss", "WIRED AI", "wired-ai", 96),
            ]
        )
        candidates.extend(
            [
                _candidate("cn1", "rss", "机器之心", "jiqizhixin", 95),
                _candidate("cn2", "rss", "量子位", "qbitai", 94),
                _candidate("cn3", "rss", "36氪", "36kr", 93),
                _candidate("cn4", "rss", "虎嗅", "huxiu", 92),
                _candidate("cn5", "rss", "钛媒体", "tmtpost", 91),
            ]
        )
        candidates.extend(
            [
                _candidate("hot1", "hotlist", "知乎", "zhihu", 90),
                _candidate("hot2", "hotlist", "微博", "weibo", 89),
                _candidate("hot3", "hotlist", "抖音", "douyin", 88),
            ]
        )

        selected = _apply_source_mix(candidates, 8, self.settings)
        mix_cfg = _source_mix_config(self.settings)
        bucket_counts = {"english_authority": 0, "chinese_ai_tech": 0, "hotlist_trend": 0}
        for item in selected:
            bucket_counts[_categorize_source_kind(item, mix_cfg)] += 1

        self.assertEqual(len(selected), 8)
        self.assertEqual(bucket_counts["english_authority"], 5)
        self.assertEqual(bucket_counts["chinese_ai_tech"], 2)
        self.assertEqual(bucket_counts["hotlist_trend"], 1)

    def test_apply_source_mix_backfills_when_bucket_insufficient(self) -> None:
        candidates = [
            _candidate("en1", "rss", "OpenAI News", "openai-news", 100),
            _candidate("cn1", "rss", "机器之心", "j1", 99),
            _candidate("cn2", "rss", "量子位", "j2", 98),
            _candidate("cn3", "rss", "36氪", "j3", 97),
            _candidate("cn4", "rss", "虎嗅", "j4", 96),
            _candidate("hot1", "hotlist", "知乎", "zhihu", 95),
            _candidate("hot2", "hotlist", "微博", "weibo", 94),
            _candidate("hot3", "hotlist", "抖音", "douyin", 93),
        ]
        selected = _apply_source_mix(candidates, 8, self.settings)
        mix_cfg = _source_mix_config(self.settings)
        english_count = sum(1 for item in selected if _categorize_source_kind(item, mix_cfg) == "english_authority")
        self.assertEqual(len(selected), 8)
        self.assertEqual(english_count, 1)

    def test_source_priority_supports_config_boosts_and_downweights(self) -> None:
        config = {
            "enabled": True,
            "boosts": {"custom source": 9},
            "downweights": {"zhihu": -15},
        }
        self.assertGreaterEqual(_source_priority_boost("Custom Source", "custom-id", config), 9)
        self.assertLessEqual(_source_priority_boost("知乎", "zhihu", config), -12)

    def test_source_priority_boost_supports_grok_and_gemini(self) -> None:
        self.assertGreater(_source_priority_boost("xAI Grok", "grok-news"), 0)
        self.assertGreater(_source_priority_boost("Google Gemini", "gemini-blog"), 0)

    def test_apply_source_mix_places_english_authority_near_top(self) -> None:
        candidates = [
            _candidate("hot1", "hotlist", "知乎", "zhihu", 100),
            _candidate("en1", "rss", "OpenAI News", "openai-news", 96),
            _candidate("en2", "rss", "Anthropic News", "anthropic-news", 95),
            _candidate("en3", "rss", "Google DeepMind", "deepmind-blog", 94),
            _candidate("en4", "rss", "The Verge", "the-verge", 93),
            _candidate("en5", "rss", "xAI Grok", "grok-news", 92),
            _candidate("cn1", "rss", "机器之心", "jiqizhixin", 91),
            _candidate("cn2", "rss", "36氪", "36kr", 90),
        ]
        selected = _apply_source_mix(candidates, 8, self.settings)
        self.assertEqual(selected[0].source_name, "OpenAI News")

    def test_is_ai_related_rejects_social_ai_news_without_focus(self) -> None:
        assistant_sources = {
            "platform_ids": [],
            "rss_ids": [],
            "title_keywords": [],
            "tech_keywords": [],
            "exclude_keywords": [],
        }
        related = _is_ai_related(
            title="某地 AI 公益活动引发市民热议",
            source_name="本地社会新闻",
            source_id="local-news",
            assistant_sources=assistant_sources,
        )
        self.assertFalse(related)


if __name__ == "__main__":
    unittest.main()
