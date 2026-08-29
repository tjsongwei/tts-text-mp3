import unittest

from core.file_reader import Chapter, split_chapters_by_chars


class SplitChaptersByCharsTests(unittest.TestCase):
    def test_short_text_stays_in_one_part(self):
        result = split_chapters_by_chars([Chapter(1, "Title", "短い本文。")], 2000)

        self.assertEqual([(1, "Part 001", "短い本文。")], [
            (part.index, part.title, part.text) for part in result
        ])

    def test_uses_last_sentence_boundary_within_limit(self):
        result = split_chapters_by_chars(
            [Chapter(1, "Title", "12345。6789。abc")], 10
        )

        self.assertEqual(["12345。", "6789。abc"], [part.text for part in result])

    def test_newline_is_a_boundary_and_is_preserved(self):
        text = "1234\n567890"
        result = split_chapters_by_chars([Chapter(1, "Title", text)], 7)

        self.assertEqual(["1234\n", "567890"], [part.text for part in result])
        self.assertEqual(text, "".join(part.text for part in result))

    def test_hard_splits_when_there_is_no_boundary(self):
        text = "abcdefghij"
        result = split_chapters_by_chars([Chapter(1, "Title", text)], 4)

        self.assertEqual(["abcd", "efgh", "ij"], [part.text for part in result])
        self.assertEqual(text, "".join(part.text for part in result))

    def test_joins_epub_chapters_in_document_order(self):
        chapters = [
            Chapter(1, "One", "abc。"),
            Chapter(2, "Two", "def。"),
        ]
        result = split_chapters_by_chars(chapters, 6)

        self.assertEqual("abc。\ndef。", "".join(part.text for part in result))
        self.assertTrue(all(len(part.text) <= 6 for part in result))

    def test_exact_limit_and_trailing_remainder(self):
        result = split_chapters_by_chars([Chapter(1, "Title", "1234567")], 5)

        self.assertEqual(["12345", "67"], [part.text for part in result])

    def test_ignores_empty_input(self):
        result = split_chapters_by_chars([Chapter(1, "Title", "  ")], 5)

        self.assertEqual([], result)

    def test_rejects_invalid_limits(self):
        for value in (0, -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                split_chapters_by_chars([], value)


if __name__ == "__main__":
    unittest.main()
