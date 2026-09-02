import tempfile
import unittest
from pathlib import Path

from core.file_reader import Chapter
from core.tts_engine import extract_preview_text, generate_chapters


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


class GenerateChaptersTests(unittest.TestCase):
    def test_completed_callback_runs_only_after_each_file_is_generated(self):
        events = []
        chapters = [Chapter(1, "One", "first"), Chapter(2, "Two", "second")]

        class Provider:
            def generate_audio(self, text, voice, output_path, **_kwargs):
                Path(output_path).write_bytes(text.encode())

        with tempfile.TemporaryDirectory() as directory:
            outputs = generate_chapters(
                Provider(),
                chapters,
                "voice",
                directory,
                completed_cb=lambda current, total, chapter, path: events.append(
                    (current, total, chapter.title, Path(path).exists())
                ),
            )

        self.assertEqual(2, len(outputs))
        self.assertEqual([(1, 2, "One", True), (2, 2, "Two", True)], events)


if __name__ == "__main__":
    unittest.main()
