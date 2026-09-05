"""Shared synthetic EPUB cases also run through the mobile reader."""
import io
import json
from pathlib import Path
import re
import unittest
import zipfile

from bs4 import BeautifulSoup

from core.file_reader import read_epub_file, split_chapters_by_chars


CASES = json.loads((Path(__file__).parent / "fixtures/epub_cases.json").read_text(encoding="utf-8"))


def epub_bytes(case):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in case["resources"].items():
            archive.writestr(name, content.encode(case.get("encodings", {}).get(name, "utf-8")))
    stream.seek(0)
    return stream


class EpubReaderTests(unittest.TestCase):
    def test_shared_cases(self):
        for case in CASES:
            with self.subTest(case=case["name"]):
                chapters = read_epub_file(epub_bytes(case))
                self.assertEqual(case["expected"], [dict(title=c.title, text=c.text) for c in chapters])
                self.assertEqual(list(range(1, len(chapters) + 1)), [c.index for c in chapters])

    def test_preserves_all_body_text_once_and_character_splitting(self):
        for case in CASES:
            with self.subTest(case=case["name"]):
                chapters = read_epub_file(epub_bytes(case))
                source = []
                for name, content in case["resources"].items():
                    if not name.endswith(".xhtml") or name.endswith("nav.xhtml"):
                        continue
                    soup = BeautifulSoup(content.split("?>")[-1], "lxml")
                    for tag in soup(["script", "style"]):
                        tag.decompose()
                    source.append(soup.body.get_text())
                normalize = lambda s: re.sub(r"\s+", "", s)
                self.assertEqual(normalize("".join(source)), normalize("".join(c.text for c in chapters)))
                parts = split_chapters_by_chars(chapters, 12)
                self.assertTrue(all(len(c.text) <= 12 for c in parts))
                self.assertEqual(normalize("".join(source)), normalize("".join(c.text for c in parts)))


if __name__ == "__main__":
    unittest.main()
