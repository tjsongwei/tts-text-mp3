"""TTSプロバイダのファクトリ"""

from core.providers.base import CancelledError, ProviderError, TTSProvider  # noqa: F401

_PROVIDER_CLASSES: dict[str, str] = {
    "edge": "core.providers.edge.EdgeTTSProvider",
    "azure": "core.providers.azure.AzureTTSProvider",
    "google": "core.providers.google.GoogleTTSProvider",
    "openai": "core.providers.openai.OpenAITTSProvider",
}


def get_provider(name: str) -> TTSProvider:
    dotted = _PROVIDER_CLASSES.get(name)
    if dotted is None:
        raise ProviderError(f"不明なプロバイダ: {name}")
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


def all_providers() -> list[tuple[str, str]]:
    """(name, label) のリストを返す"""
    result = []
    for name in _PROVIDER_CLASSES:
        provider = get_provider(name)
        result.append((provider.name, provider.label))
    return result
