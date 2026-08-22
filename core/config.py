"""APIキー等の認証情報管理（~/.tts-text-mp3/config.json）"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".tts-text-mp3"
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULTS: dict = {"providers": {}, "last_provider": "edge", "last_output_dir": ""}


def _load() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in _DEFAULTS})
    return merged


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_provider_credentials(provider_name: str) -> dict:
    data = _load()
    return data["providers"].get(provider_name, {})


def set_provider_credentials(provider_name: str, credentials: dict) -> None:
    data = _load()
    data.setdefault("providers", {})[provider_name] = credentials
    save(data)


def get_last(key: str):
    return _load().get(key)


def set_last(key: str, value) -> None:
    data = _load()
    data[key] = value
    save(data)


def config_path() -> Path:
    return CONFIG_FILE
