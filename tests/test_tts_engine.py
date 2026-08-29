import unittest

from core.tts_engine import extract_preview_text


class ExtractPreviewTextTests(unittest.TestCase):
    def test_uses_sentence_boundary_near_target_length(self):
        text = "a" * 70 + "。" + "b" * 20 + "。" + "c" * 20

        self.assertEqual("a" * 70 + "。" + "b" * 20 + "。", extract_preview_text(text, 100))

    def test_does_not_stop_at_a_very_early_sentence_boundary(self):
        text = "短い。" + "a" * 200

        self.assertEqual(100, len(extract_preview_text(text, 100)))

    def test_short_text_is_returned_in_full(self):
        self.assertEqual("短い本文。", extract_preview_text("短い本文。", 150))

    def test_non_positive_limit_returns_empty_text(self):
        self.assertEqual("", extract_preview_text("本文", 0))


if __name__ == "__main__":
    unittest.main()
