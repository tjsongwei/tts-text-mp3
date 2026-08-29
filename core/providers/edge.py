"""Microsoft Edge TTS プロバイダ（無料・認証不要）"""

import asyncio
from pathlib import Path
from typing import Callable

import edge_tts
from i18n import t

from core.providers.base import (
    PROGRESS_INTERVAL,
    TTSProvider,
    check_cancel,
)


class EdgeTTSProvider(TTSProvider):
    name = "edge"

    @property
    def label(self) -> str:
        return t("provider.edge.label")

    def requires_credentials(self) -> dict[str, str]:
        return {}

    def validate_credentials(self) -> None:
        return None

    def list_voices(self) -> list[dict]:
        voices = asyncio.run(edge_tts.list_voices())
        return [
            {
                "ShortName": v["ShortName"],
                "Gender": v.get("Gender", ""),
                "Locale": v.get("Locale", ""),
            }
            for v in voices
        ]

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
        communicate = edge_tts.Communicate(
            text, voice, rate=rate, volume=volume, pitch=pitch
        )
        written = 0
        next_report = PROGRESS_INTERVAL
        with open(output_path, "wb") as audio:
            for chunk in communicate.stream_sync():
                check_cancel(cancel_event)
                if chunk["type"] == "audio":
                    data = chunk["data"]
                    audio.write(data)
                    written += len(data)
                    if progress_cb is not None and written >= next_report:
                        progress_cb(written)
                        next_report = written + PROGRESS_INTERVAL
        if progress_cb is not None:
            progress_cb(written)
