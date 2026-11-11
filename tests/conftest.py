"""Default tests never call external HTTP or a paid model."""

import pytest
import requests


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in (
        "DEFAULT_LLM_PROVIDER",
        "DEFAULT_MODEL_NAME",
        "DEMO_MODE",
        "COINGECKO_PLAN",
        "COINGECKO_API_KEY",
        "TAVILY_API_KEY",
        "LLM_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    for provider in ("OPENAI", "ANTHROPIC", "DEEPSEEK", "GEMINI"):
        monkeypatch.setenv(f"{provider}_API_KEY", "offline-test-credential")
        monkeypatch.delenv(f"{provider}_BASE_URL", raising=False)

    def no_http(*args, **kwargs):
        raise AssertionError("Tests must provide an HTTP fixture")

    monkeypatch.setattr(requests, "request", no_http)
