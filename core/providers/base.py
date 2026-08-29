"""TTSプロバイダ共通インターフェース"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from i18n import t


class ProviderError(Exception):
    pass


class CancelledError(Exception):
    pass


def parse_percent(value: str) -> int:
    m = re.fullmatch(r"([+-]?\d+)\s*%", value.strip())
    if not m:
        raise ValueError(t("error.invalid_percent", value=value))
    return int(m.group(1))


def parse_hz(value: str) -> int:
    m = re.fullmatch(r"([+-]?\d+)\s*Hz", value.strip())
    if not m:
        raise ValueError(t("error.invalid_hz", value=value))
    return int(m.group(1))


def check_cancel(cancel_event) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError(t("error.cancelled"))


def split_text_by_bytes(text: str, max_bytes: int, min_break: int = 200) -> list[str]:
    """文境界優先でmax_bytes以下のUTF-8チャンクに分割"""
    chunks: list[str] = []
    current = ""
    for sentence in _split_sentences(text):
        candidate = current + sentence
        if len(candidate.encode("utf-8")) <= max_bytes:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(sentence.encode("utf-8")) <= max_bytes:
            current = sentence
        else:
            current = ""
            piece = ""
            for char in sentence:
                if len((piece + char).encode("utf-8")) > max_bytes:
                    chunks.append(piece)
                    piece = char
                else:
                    piece += char
            current = piece
    if current.strip():
        chunks.append(current)
    return [c for c in (s.strip() for s in chunks) if c]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。．.!?！？\n])", text)
    return [p for p in parts if p]


class TTSProvider(ABC):
    name: str = ""
    label: str = ""

    @abstractmethod
    def requires_credentials(self) -> dict[str, str]:
        """必須認証フィールド {field_name: 説明} を返す"""

    def optional_credentials(self) -> dict[str, str]:
        return {}

    @abstractmethod
    def validate_credentials(self) -> None:
        """認証情報が設定済みか確認。未設定なら ProviderError を投げる"""

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """{ShortName, Gender, Locale} 形式のリストを返す"""

    @abstractmethod
    def generate_audio(
        self,
        text: str,
        voice: str,
        output_path: str | Path,
        *,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        progress_cb: Callable[[int], None] | None = None,
        cancel_event=None,
    ) -> None:
        """textをMP3ファイルとしてoutput_pathへ出力する"""


PROGRESS_INTERVAL = 64 * 1024
