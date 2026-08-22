"""Google Cloud Text-to-Speech プロバイダ"""

import json
import os
import time
from pathlib import Path
from typing import Callable

from core.config import get_provider_credentials
from core.providers.base import (
    PROGRESS_INTERVAL,
    ProviderError,
    TTSProvider,
    check_cancel,
    parse_hz,
    parse_percent,
    split_text_by_bytes,
)

_MAX_CHUNK_BYTES = 3800
_MIN_RETRY_CHUNK_BYTES = 24
_VOICE_LIST_ATTEMPTS = 3


class GoogleTTSProvider(TTSProvider):
    name = "google"
    label = "Google Cloud TTS"

    def requires_credentials(self) -> dict[str, str]:
        return {}

    def optional_credentials(self) -> dict[str, str]:
        return {
            "api_key": "APIキー（サービスアカウントJSONキーの代わりに使用可）",
            "credentials_json": "サービスアカウントJSONキーのパス（client_secret_*.jsonは不可）",
        }

    def _client(self):
        from google.api_core.client_options import ClientOptions
        from google.cloud import texttospeech

        creds = get_provider_credentials(self.name)
        api_key = creds.get("api_key", "").strip()
        cred_path = creds.get("credentials_json", "").strip()
        if not api_key and not cred_path:
            raise ProviderError(
                "Google Cloudの認証情報が未設定です（設定ダイアログで入力してください）"
            )
        if api_key:
            return texttospeech.TextToSpeechClient(
                client_options=ClientOptions(api_key=api_key)
            )
        path = Path(cred_path)
        if not path.is_file():
            raise ProviderError(f"認証JSONファイルが見つかりません: {path}")
        self._validate_key_file(path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
        return texttospeech.TextToSpeechClient()

    @staticmethod
    def _validate_key_file(path: Path) -> None:
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise ProviderError(f"認証JSONを読み込めません: {e}") from e
        file_type = data.get("type") if isinstance(data, dict) else None
        if "installed" in data or "web" in data:
            raise ProviderError(
                f"このファイルはOAuthクライアントシークレットです（{path.name}）。\n"
                "サービスアカウントのJSONキーが必要です:\n"
                "GCPコンソール → IAMと管理 → サービス アカウント → 作成 → "
                "「Cloud Text-to-Speech ユーザー」ロールを付与 → "
                "キー → 鍵を追加 → JSON でダウンロードしてください。"
                "または設定ダイアログでAPIキーを入力してください。"
            )
        if file_type != "service_account":
            raise ProviderError(
                f"認証JSONの形式が不正です（type={file_type}）。"
                "サービスアカウントのJSONキーまたはAPIキーを指定してください。"
            )

    def validate_credentials(self) -> None:
        self._client()

    @staticmethod
    def _translate_error(e: Exception) -> ProviderError | None:
        msg = str(e)
        if "has not been used in project" in msg or (
            "is disabled" in msg and "texttospeech" in msg.lower()
        ):
            return ProviderError(
                "Cloud Text-to-Speech APIが有効化されていません。\n"
                "GCPコンソールでAPIを有効にしてから再試行してください:\n"
                "APIとサービス → ライブラリ → 「Cloud Text-to-Speech API」→ 有効にする\n"
                f"詳細: {e}"
            )
        if "PERMISSION_DENIED" in msg or "403" in msg:
            return ProviderError(
                "アクセスが拒否されました。サービスアカウントに"
                "「Cloud Text-to-Speech ユーザー」ロールが付与されているか確認してください。\n"
                f"詳細: {e}"
            )
        if "UNAUTHENTICATED" in msg or "invalid_grant" in msg:
            return ProviderError(
                "認証に失敗しました。JSONキーが無効または失効している可能性があります。\n"
                f"詳細: {e}"
            )
        if "QUOTA" in msg.upper() or "RESOURCE_EXHAUSTED" in msg:
            return ProviderError(f"利用制限（クォータ）に達しました。\n詳細: {e}")
        return None

    @staticmethod
    def _is_too_long_error(e: Exception) -> bool:
        msg = str(e).lower()
        return any(
            phrase in msg
            for phrase in (
                "too long",
                "input size",
                "content size",
                "maximum allowed size",
                "5000 bytes",
                "4000 bytes",
            )
        )

    @staticmethod
    def _is_transient_error(e: Exception) -> bool:
        msg = str(e).lower()
        return any(
            phrase in msg
            for phrase in (
                "unavailable",
                "deadline exceeded",
                "deadline_exceeded",
                "connection reset",
                "connection aborted",
                "temporarily unavailable",
                "timed out",
                "timeout",
                "503",
            )
        )

    def list_voices(self) -> list[dict]:
        from google.cloud import texttospeech

        client = self._client()
        for attempt in range(_VOICE_LIST_ATTEMPTS):
            try:
                response = client.list_voices()
                raw_voices = list(response.voices)
                break
            except Exception as e:
                if self._is_transient_error(e) and attempt + 1 < _VOICE_LIST_ATTEMPTS:
                    time.sleep(attempt + 1)
                    continue
                translated = self._translate_error(e)
                if translated is not None:
                    raise translated from e
                raise ProviderError(f"Googleボイス一覧の取得に失敗: {e}") from e
        gender_map = {
            texttospeech.SsmlVoiceGender.FEMALE: "Female",
            texttospeech.SsmlVoiceGender.MALE: "Male",
        }
        result = []
        for v in raw_voices:
            result.append(
                {
                    "ShortName": v.name,
                    "Gender": gender_map.get(v.ssml_gender, ""),
                    "Locale": v.language_codes[0] if v.language_codes else "",
                    "_language_codes": list(v.language_codes),
                }
            )
        return result

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
        from google.cloud import texttospeech

        client = self._client()

        rate_pct = parse_percent(rate)
        vol_pct = parse_percent(volume)
        pitch_hz = parse_hz(pitch)
        speaking_rate = max(0.25, min(4.0, 1 + rate_pct / 100))
        volume_gain_db = max(-32.0, min(16.0, vol_pct / 50 * 6))
        pitch_semitones = max(-20.0, min(20.0, pitch_hz / 25))

        language_code = self._resolve_language_code(voice)
        chunks = split_text_by_bytes(text, _MAX_CHUNK_BYTES)

        written = 0
        next_report = PROGRESS_INTERVAL
        with open(output_path, "wb") as audio:
            def synthesize_chunk(chunk: str) -> None:
                nonlocal written, next_report
                check_cancel(cancel_event)
                synthesis_input = texttospeech.SynthesisInput(text=chunk)
                voice_params = texttospeech.VoiceSelectionParams(
                    language_code=language_code, name=voice
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=speaking_rate,
                    volume_gain_db=volume_gain_db,
                    pitch=pitch_semitones,
                )
                try:
                    response = client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice_params,
                        audio_config=audio_config,
                    )
                except Exception as e:
                    chunk_bytes = len(chunk.encode("utf-8"))
                    if self._is_too_long_error(e) and chunk_bytes > _MIN_RETRY_CHUNK_BYTES:
                        retry_limit = max(_MIN_RETRY_CHUNK_BYTES, chunk_bytes // 2)
                        retry_chunks = split_text_by_bytes(chunk, retry_limit)
                        if len(retry_chunks) > 1:
                            for retry_chunk in retry_chunks:
                                synthesize_chunk(retry_chunk)
                            return
                    translated = self._translate_error(e)
                    if translated is not None:
                        raise translated from e
                    raise ProviderError(f"Google TTSでエラー: {e}") from e
                data = response.audio_content
                audio.write(data)
                written += len(data)
                if progress_cb is not None and written >= next_report:
                    progress_cb(written)
                    next_report = written + PROGRESS_INTERVAL

            for chunk in chunks:
                synthesize_chunk(chunk)
        if progress_cb is not None:
            progress_cb(written)

    def _resolve_language_code(self, voice: str) -> str:
        if "-" in voice and voice.split("-")[0].isalpha() and len(voice.split("-")[0]) == 2:
            return "-".join(voice.split("-")[:2])
        try:
            for v in self.list_voices():
                if v["ShortName"] == voice:
                    codes = v.get("_language_codes") or []
                    if codes:
                        return codes[0]
        except Exception:
            pass
        return "en-US"
