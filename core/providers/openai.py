"""OpenAI TTS プロバイダ"""

from pathlib import Path
from typing import Callable

from i18n import t
from core.config import get_provider_credentials
from core.providers.base import (
    PROGRESS_INTERVAL,
    ProviderError,
    TTSProvider,
    check_cancel,
    parse_percent,
)

_MAX_CHUNK_CHARS = 4000

_OPENAI_VOICES = [
    ("alloy", ""),
    ("ash", ""),
    ("ballad", ""),
    ("coral", ""),
    ("echo", ""),
    ("fable", ""),
    ("onyx", ""),
    ("nova", ""),
    ("sage", ""),
    ("shimmer", ""),
]


class OpenAITTSProvider(TTSProvider):
    name = "openai"
    label = "OpenAI TTS"

    def requires_credentials(self) -> dict[str, str]:
        return {"api_key": t("provider.openai.api_key")}

    def optional_credentials(self) -> dict[str, str]:
        return {"model": t("provider.openai.model")}

    def validate_credentials(self) -> None:
        creds = get_provider_credentials(self.name)
        if not creds.get("api_key", "").strip():
            raise ProviderError(t("provider.openai.credentials"))

    def _client(self):
        from openai import OpenAI

        creds = get_provider_credentials(self.name)
        api_key = creds.get("api_key", "").strip()
        if not api_key:
            raise ProviderError(t("provider.openai.credentials"))
        return OpenAI(api_key=api_key), creds.get("model", "tts-1").strip() or "tts-1"

    def list_voices(self) -> list[dict]:
        self.validate_credentials()
        return [
            {"ShortName": name, "Gender": gender, "Locale": "en-US"}
            for name, gender in _OPENAI_VOICES
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
        client, model = self._client()
        speed = max(0.25, min(4.0, 1 + parse_percent(rate) / 100))
        kwargs = {"model": model, "voice": voice, "response_format": "mp3"}
        if model.startswith("tts-1"):
            kwargs["speed"] = speed

        chunks = [text[i : i + _MAX_CHUNK_CHARS] for i in range(0, len(text), _MAX_CHUNK_CHARS)]
        written = 0
        next_report = PROGRESS_INTERVAL
        with open(output_path, "wb") as audio:
            for chunk in chunks:
                check_cancel(cancel_event)
                try:
                    with client.audio.speech.with_streaming_response.create(
                        input=chunk, **kwargs
                    ) as response:
                        for data in response.iter_bytes():
                            audio.write(data)
                            written += len(data)
                            if progress_cb is not None and written >= next_report:
                                progress_cb(written)
                                next_report = written + PROGRESS_INTERVAL
                except Exception as e:
                    raise ProviderError(t("provider.operation_error", provider="OpenAI TTS", error=e)) from e
        if progress_cb is not None:
            progress_cb(written)
