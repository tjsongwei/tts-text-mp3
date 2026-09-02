"""チャプター単位のMP3生成（プロバイダ経由）"""

import os
import re
from typing import Callable

from i18n import t
from core.file_reader import Chapter, sanitize_filename
from core.providers import get_provider
from core.providers.base import CancelledError, TTSProvider  # noqa: F401


def get_voices(provider: TTSProvider) -> list[dict]:
    return provider.list_voices()


def get_language_codes(voices: list[dict]) -> list[str]:
    return sorted({v["Locale"] for v in voices})


def voices_for_locale(voices: list[dict], locale: str) -> list[dict]:
    if not locale or locale == "all":
        return voices
    prefix = locale.split("-")[0]
    exact = [v for v in voices if v["Locale"] == locale]
    if exact:
        return exact
    return [v for v in voices if v["Locale"].startswith(prefix)]


def extract_preview_text(text: str, max_chars: int = 150) -> str:
    """先頭から約max_chars文字を、できるだけ文末で区切って返す。"""
    cleaned = text.strip()
    if not cleaned:
        return ""
    if max_chars <= 0:
        return ""
    window = cleaned[:max_chars]
    sentence_ends = list(re.finditer(r"[。．.!?！？\n]", window))
    if sentence_ends and sentence_ends[-1].end() >= max_chars * 0.6:
        return window[: sentence_ends[-1].end()].strip()
    return window.strip()


def generate_chapters(
    provider: TTSProvider,
    chapters: list[Chapter],
    voice: str,
    output_dir: str,
    *,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    chapter_cb: Callable[[int, int, str], None] | None = None,
    completed_cb: Callable[[int, int, Chapter, str], None] | None = None,
    progress_cb: Callable[[int], None] | None = None,
    cancel_event=None,
) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    outputs = []
    total = len(chapters)
    for i, ch in enumerate(chapters):
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError(t("error.cancelled"))
        fname = f"{ch.index:03d}_{sanitize_filename(ch.title)}.mp3"
        out_path = os.path.join(output_dir, fname)
        if chapter_cb is not None:
            chapter_cb(i + 1, total, ch.title)
        provider.generate_audio(
            ch.text,
            voice,
            out_path,
            rate=rate,
            volume=volume,
            pitch=pitch,
            progress_cb=progress_cb,
            cancel_event=cancel_event,
        )
        outputs.append(out_path)
        if completed_cb is not None:
            completed_cb(i + 1, total, ch, out_path)
    return outputs
