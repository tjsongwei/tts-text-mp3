import json
import unittest
from pathlib import Path

from core.file_reader import load_chapters
from core.providers import get_provider
from i18n import SUPPORTED_LANGUAGES, normalize_language, set_language, t


class I18nTests(unittest.TestCase):
    def tearDown(self):
        set_language("ja")

    def test_all_catalogs_have_the_same_keys(self):
        locale_dir = Path(__file__).resolve().parents[1] / "locales"
        catalogs = {
            language: json.loads((locale_dir / f"{language}.json").read_text(encoding="utf-8"))
            for language in SUPPORTED_LANGUAGES
        }
        expected = set(catalogs["en"])

        for language, catalog in catalogs.items():
            with self.subTest(language=language):
                self.assertEqual(expected, set(catalog))

    def test_each_language_translates_a_ui_label(self):
        expected = {"ja": "音声確認", "en": "Preview Audio", "zh-CN": "试听"}

        for language, label in expected.items():
            with self.subTest(language=language):
                set_language(language)
                self.assertEqual(label, t("button.preview"))

    def test_format_values_are_inserted(self):
        set_language("en")

        self.assertEqual("Complete: 3 files created", t("generate.done", count=3))

    def test_supported_language_is_preserved(self):
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(language, normalize_language(language))

    def test_provider_setting_descriptions_follow_language(self):
        expected = {
            "ja": "Speechリソースのリージョン（例: japaneast）",
            "en": "Speech resource region (example: japaneast)",
            "zh-CN": "Speech 资源区域（例如：japaneast）",
        }

        for language, description in expected.items():
            with self.subTest(language=language):
                set_language(language)
                self.assertEqual(description, get_provider("azure").requires_credentials()["region"])

    def test_core_errors_follow_language(self):
        expected = {
            "ja": "未対応のファイル形式です",
            "en": "Unsupported file format",
            "zh-CN": "不支持的文件格式",
        }

        for language, message in expected.items():
            with self.subTest(language=language):
                set_language(language)
                with self.assertRaisesRegex(ValueError, message):
                    load_chapters("book.bin")


if __name__ == "__main__":
    unittest.main()
