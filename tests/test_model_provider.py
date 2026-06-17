from researchinfra.models.adapters import OpenAICompatibleProvider
from researchinfra.models.base import ModelProviderConfigurationError
from researchinfra.schemas import ModelProviderConfig


def test_openai_compatible_provider_reports_missing_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        ModelProviderConfig(id="openai-compatible", provider="openai-compatible")
    )

    assert provider.status()["api_key"] == "missing"

    try:
        provider.complete("hello")
    except ModelProviderConfigurationError as exc:
        assert "OPENAI_API_KEY is not set" in str(exc)
    else:
        raise AssertionError("Expected missing API key to raise a clear configuration error")
