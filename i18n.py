"""UI translation resources and locale selection."""

import json
import locale
from pathlib import Path


SUPPORTED_LANGUAGES = ("ja", "en", "zh-CN")
LANGUAGE_NAMES = {"ja": "日本語", "en": "English", "zh-CN": "简体中文"}
_FALLBACK_LANGUAGE = "en"
_current_language = _FALLBACK_LANGUAGE
_catalogs: dict[str, dict[str, str]] = {}


def detect_system_language() -> str:
    language = (locale.getlocale()[0] or "").replace("_", "-").lower()
    if language.startswith("ja"):
        return "ja"
    if language.startswith("zh"):
        return "zh-CN"
    return "en"


def normalize_language(language: object) -> str:
    return language if isinstance(language, str) and language in SUPPORTED_LANGUAGES else detect_system_language()


def set_language(language: object) -> str:
    global _current_language
    _current_language = normalize_language(language)
    return _current_language


def get_language() -> str:
    return _current_language


def _load_catalog(language: str) -> dict[str, str]:
    if language not in _catalogs:
        path = Path(__file__).resolve().parent / "locales" / f"{language}.json"
        with open(path, encoding="utf-8") as file:
            _catalogs[language] = json.load(file)
    return _catalogs[language]


def t(key: str, **values) -> str:
    catalog = _load_catalog(_current_language)
    fallback = _load_catalog(_FALLBACK_LANGUAGE)
    template = catalog.get(key, fallback.get(key, key))
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template
