"""One validated configuration path for both agents, backed by SpoonOS ChatBot."""

import asyncio
import os
from collections.abc import Coroutine
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from spoon_ai.chat import ChatBot
from spoon_ai.llm.config import ConfigurationManager, ProviderConfig
from spoon_ai.llm.manager import LLMManager
from spoon_ai.llm.providers import (
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    OpenAIProvider,
)
from spoon_ai.llm.registry import LLMProviderRegistry

T = TypeVar("T")
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-2.5-flash",
}
PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider,
}
BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "deepseek": "https://api.deepseek.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
}


class ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: Literal["openai", "anthropic", "deepseek", "gemini"]
    model: str = Field(min_length=1)
    api_key: SecretStr
    timeout: float = Field(default=90, gt=0, le=600)

    @classmethod
    def from_env(cls, provider: str | None = None, model: str | None = None, *, require_key=True):
        provider = (provider or os.getenv("DEFAULT_LLM_PROVIDER", "openai")).strip().lower()
        if provider not in DEFAULT_MODELS:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        key_name = f"{provider.upper()}_API_KEY"
        key = os.getenv(key_name, "").strip()
        if not key or "your-" in key or key.startswith("<"):
            if require_key:
                raise ValueError(f"{key_name} is not configured")
            key = ""
        return cls(
            provider=provider,
            model=(model or os.getenv("DEFAULT_MODEL_NAME") or DEFAULT_MODELS[provider]).strip(),
            api_key=key,
            timeout=os.getenv("LLM_TIMEOUT_SECONDS", "90"),
        )


class _RunConfiguration(ConfigurationManager):
    """Scope SDK configuration to one selected provider, without global credentials."""

    def __init__(self, settings):
        self.config = ProviderConfig(
            name=settings.provider,
            api_key=settings.api_key.get_secret_value(),
            model=settings.model,
            base_url=os.getenv(f"{settings.provider.upper()}_BASE_URL")
            or BASE_URLS[settings.provider],
            timeout=settings.timeout,
            retry_attempts=1,
        )

    def load_provider_config(self, provider_name):
        if provider_name != self.config.name:
            raise ValueError("Provider is outside this run's configuration")
        return self.config

    def list_configured_providers(self):
        return [self.config.name]

    def get_default_provider(self):
        return self.config.name

    def get_fallback_chain(self):
        return [self.config.name]


class _RunLLMManager(LLMManager):
    # SDK 0.4.10 ChatBot.ask does not forward model_name. Bind it per request,
    # so another report/model cannot inherit a previously initialized provider's model.
    def _register_cleanup(self):
        pass  # Callers explicitly await cleanup; avoid registering an atexit hook per request.

    async def chat(self, messages, provider=None, **kwargs):
        kwargs.setdefault("model", self.config_manager.load_provider_config(provider).model)
        return await super().chat(messages, provider=provider, **kwargs)

    async def chat_with_tools(self, messages, tools, provider=None, **kwargs):
        kwargs.setdefault("model", self.config_manager.load_provider_config(provider).model)
        return await super().chat_with_tools(messages, tools, provider=provider, **kwargs)


class _ResearchChatBot(ChatBot):
    def __init__(self, settings):
        self.research_settings = settings
        super().__init__(
            llm_provider=settings.provider,
            model_name=settings.model,
            api_key=settings.api_key.get_secret_value(),
            enable_short_term_memory=False,
            enable_long_term_memory=False,
        )

    def _initialize_with_priority(self):
        settings = self.research_settings
        registry = LLMProviderRegistry()
        registry.register(settings.provider, PROVIDERS[settings.provider])
        self.llm_manager = _RunLLMManager(
            config_manager=_RunConfiguration(settings), registry=registry
        )


def create_chatbot(settings: ModelSettings) -> ChatBot:
    if not settings.api_key.get_secret_value():
        raise ValueError(f"{settings.provider.upper()}_API_KEY is not configured")
    return _ResearchChatBot(settings)


def run_sync(coroutine: Coroutine[Any, Any, T]) -> T:
    """Keep CLI compatibility; servers/notebooks must await arun instead."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    coroutine.close()
    raise RuntimeError("An event loop is running; use 'await agent.arun(...)' instead of run().")
