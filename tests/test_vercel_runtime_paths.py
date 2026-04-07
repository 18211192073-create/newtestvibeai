import os
import unittest
from unittest.mock import patch

from trendradar.assistant.digest import _assistant_output_dir
from trendradar.assistant.storage import _default_data_dir


class VercelRuntimePathsTests(unittest.TestCase):
    def test_storage_uses_tmp_dir_on_vercel(self) -> None:
        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
            path = _default_data_dir()
            self.assertIn("/tmp/day-vibe-ai/assistant", str(path))

    def test_digest_output_uses_tmp_dir_on_vercel(self) -> None:
        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
            path = _assistant_output_dir()
            self.assertIn("/tmp/day-vibe-ai/assistant", str(path))


if __name__ == "__main__":
    unittest.main()
