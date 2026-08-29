"""Microsoft Azure Speech プロバイダ（公式・有料/無料枠あり）"""

import re
from xml.sax.saxutils import escape

import requests
from i18n import t

from core.config import get_provider_credentials
from core.providers.base import (
    PROGRESS_INTERVAL,
    ProviderError,
    TTSProvider,
    check_cancel,
)

_MAX_CHUNK_CHARS = 2000
_VOICE_LIST_URL = "https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"


class AzureTTSProvider(TTSProvider):
    name = "azure"
    label = "Microsoft Azure Speech"

    def requires_credentials(self) -> dict[str, str]:
        return {
            "key": t("provider.azure.key"),
            "region": t("provider.azure.region"),
        }

    def _credentials(self) -> tuple[str, str]:
        creds = get_provider_credentials(self.name)
        key = creds.get("key", "").strip()
        region = creds.get("region", "").strip()
        if not key or not region:
            raise ProviderError(t("provider.azure.credentials"))
        return key, region

    def validate_credentials(self) -> None:
        self._credentials()

    def list_voices(self) -> list[dict]:
        key, region = self._credentials()
        url = _VOICE_LIST_URL.format(region=region)
        try:
            resp = requests.get(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ProviderError(t("provider.voice_list_error", provider="Azure", error=e)) from e
        return [
            {
                "ShortName": v["ShortName"],
                "Gender": v.get("Gender", ""),
                "Locale": v.get("Locale", ""),
            }
            for v in resp.json()
        ]

    def generate_audio(self, text, voice, output_path, *, rate="+0%", volume="+0%", pitch="+0Hz",
                       progress_cb=None, cancel_event=None) -> None:
        import azure.cognitiveservices.speech as speechsdk

        key, region = self._credentials()
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
        )
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=None
        )

        lang = "-".join(voice.split("-")[:2])
        chunks = self._split_chunks(text)
        written = 0
        next_report = PROGRESS_INTERVAL
        with open(output_path, "wb") as audio:
            for chunk in chunks:
                check_cancel(cancel_event)
                ssml = (
                    "<speak version='1.0' "
                    "xmlns='http://www.w3.org/2001/10/synthesis' "
                    f"xml:lang='{lang}'>"
                    f"<voice name='{voice}'>"
                    f"<prosody rate='{rate}' volume='{volume}' pitch='{pitch}'>"
                    f"{escape(chunk)}"
                    "</prosody></voice></speak>"
                )
                result = synthesizer.speak_ssml_async(ssml).get()
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    data = result.audio_data
                    audio.write(data)
                    written += len(data)
                    if progress_cb is not None and written >= next_report:
                        progress_cb(written)
                        next_report = written + PROGRESS_INTERVAL
                elif result.reason == speechsdk.ResultReason.Canceled:
                    details = result.cancellation_details
                    raise ProviderError(t("provider.operation_error", provider="Azure TTS", error=details.error_details))
                else:
                    raise ProviderError(t("provider.operation_error", provider="Azure TTS", error=result.reason))
        if progress_cb is not None:
            progress_cb(written)

    @staticmethod
    def _split_chunks(text: str) -> list[str]:
        parts = re.split(r"(?<=[。．.!?\n])", text)
        chunks: list[str] = []
        current = ""
        for part in parts:
            if not part:
                continue
            if len(current) + len(part) <= _MAX_CHUNK_CHARS:
                current += part
            else:
                if current.strip():
                    chunks.append(current)
                while len(part) > _MAX_CHUNK_CHARS:
                    chunks.append(part[:_MAX_CHUNK_CHARS])
                    part = part[_MAX_CHUNK_CHARS:]
                current = part
        if current.strip():
            chunks.append(current)
        return [c for c in chunks if c.strip()]
