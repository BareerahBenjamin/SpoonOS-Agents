import json
from unittest.mock import AsyncMock

import pytest
from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.llm.interface import LLMResponse
from spoon_ai.llm.manager import LLMManager
from spoon_ai.schema import Function, ToolCall

from agents.graph_agent import CryptoAnalysisGraph
from agents.react_agent import CryptoReActAgent
from agents.runtime import ModelSettings, create_chatbot
from tools.base import utc_now
from tools.crypto_tools import CryptoHistoryTool, CryptoNewsTool, CryptoPriceTool


def history():
    return {
        "status": "live",
        "source": "https://api.coingecko.com/history",
        "fetched_at": utc_now(),
        "prices": [[i * 86400000, 100 + i] for i in range(120)],
    }


def model_report(**overrides):
    return json.dumps(
        {
            "recommendation": "SELL",
            "summary": "需谨慎",
            "reasoning": "证据存在风险",
            "evidence_ids": ["price"],
            "limitations": [],
            **overrides,
        }
    )


@pytest.fixture
def graph_sources(monkeypatch):
    monkeypatch.setattr(
        CryptoPriceTool,
        "execute",
        AsyncMock(
            return_value={
                "status": "live",
                "source": "https://api.coingecko.com/price",
                "fetched_at": utc_now(),
                "current_price": 50000,
                "price_change_percentage_24h": 2,
            }
        ),
    )
    monkeypatch.setattr(CryptoHistoryTool, "execute", AsyncMock(return_value=history()))
    monkeypatch.setattr(
        CryptoNewsTool,
        "execute",
        AsyncMock(
            return_value={
                "status": "live",
                "source": "tavily",
                "fetched_at": utc_now(),
                "articles": [
                    {
                        "url": "https://news.example/article",
                        "title": "News",
                        "content": "Evidence",
                        "published_at": "2026-10-27",
                        "source": "news.example",
                    }
                ],
            }
        ),
    )
    ask = AsyncMock(return_value=model_report())
    monkeypatch.setattr(ChatBot, "ask", ask)
    return ask


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "anthropic", "deepseek", "gemini"])
async def test_real_spoon_toolcall_loop_and_multiline_json(monkeypatch, provider):
    calls = []
    responses = iter(
        [
            LLMResponse(
                content="",
                provider=provider,
                model="test-model",
                native_finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        id="price-1",
                        function=Function(
                            name="get_crypto_price", arguments='{\n  "symbol": "btc"\n}'
                        ),
                    )
                ],
                finish_reason="tool_calls",
            ),
            LLMResponse(
                content="演示行情为 50000 USD，不能用于投资判断。",
                finish_reason="stop",
                provider=provider,
                model="test-model",
                native_finish_reason="stop",
            ),
        ]
    )

    async def provider_operation(self, provider_name, operation, *args, **kwargs):
        calls.append((provider_name, operation, kwargs))
        return next(responses)

    # Only the external inference boundary is replaced; ChatBot, ToolCallAgent,
    # ToolManager, tool schema/validation and the execution loop are the actual SDK.
    monkeypatch.setattr(LLMManager, "_execute_provider_operation", provider_operation)
    agent = CryptoReActAgent(
        llm_provider=provider, model_name="test-model", demo_mode=True, verbose=False
    )
    answer = await agent.arun("BTC 价格是多少？")
    assert isinstance(agent.agent, ToolCallAgent)
    assert "50000" in answer
    assert len(calls) == 2
    assert calls[0][0] == provider
    assert all(call[2]["model"] == "test-model" for call in calls)
    assert any(message.role == "tool" and "mock" in message.content for message in agent.history)
    assert "get_crypto_price" in {
        tool["function"]["name"] for tool in agent.agent.available_tools.to_params()
    }


@pytest.mark.asyncio
async def test_graph_keeps_model_and_rule_separate(graph_sources):
    result = await CryptoAnalysisGraph(verbose=False).arun("btc")
    assert result.status == "completed"
    assert result.recommendation == "SELL"
    assert result.rule_signal == "HOLD"
    assert result.disagreement is True
    assert result.confidence is None
    assert result.data["technical_indicators"]["rsi"] == 100
    assert result.snapshot_id in graph_sources.call_args.kwargs["messages"][0]["content"]
    assert all(row["snapshot_id"] == result.snapshot_id for row in result.evidence)
    assert [row["sequence"] for row in result.events] == list(range(1, len(result.events) + 1))


@pytest.mark.asyncio
async def test_missing_price_stops_model(graph_sources, monkeypatch):
    monkeypatch.setattr(
        CryptoPriceTool,
        "execute",
        AsyncMock(
            return_value={
                "status": "unavailable",
                "error": "HTTP 429",
                "source": "coingecko",
                "fetched_at": utc_now(),
            }
        ),
    )
    result = await CryptoAnalysisGraph().arun("BTC")
    assert result.status == "unavailable"
    assert result.recommendation is None
    assert result.rule_signal is None
    graph_sources.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_news_and_history_yields_partial_report(graph_sources, monkeypatch):
    for tool in (CryptoNewsTool, CryptoHistoryTool):
        monkeypatch.setattr(
            tool,
            "execute",
            AsyncMock(
                return_value={
                    "status": "unavailable",
                    "error": "not configured",
                    "source": "source",
                    "fetched_at": utc_now(),
                }
            ),
        )
    result = await CryptoAnalysisGraph().arun("ETH")
    assert result.status == "partial"
    assert len(result.limitations) == 2
    assert result.model_report is not None
    assert result.data["technical_indicators"]["status"] == "unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        "not json",
        model_report(recommendation="MOON"),
        model_report(evidence_ids=["price", "invented"]),
        model_report(evidence_ids=["news-1"]),
        model_report(confidence=75),
    ],
)
async def test_invalid_model_report_is_not_published(response, graph_sources):
    graph_sources.return_value = response
    result = await CryptoAnalysisGraph().arun("BTC")
    assert result.status == "failed"
    assert result.model_report is None
    assert result.recommendation is None
    assert "validation failed" in result.reasoning


@pytest.mark.asyncio
async def test_timeout_is_a_failed_report(graph_sources):
    graph_sources.side_effect = TimeoutError()
    result = await CryptoAnalysisGraph().arun("BTC")
    assert result.status == "failed"
    assert result.events[-1]["status"] == "failed"


@pytest.mark.asyncio
async def test_demo_never_generates_directional_conclusion(monkeypatch):
    ask = AsyncMock()
    monkeypatch.setattr(ChatBot, "ask", ask)
    result = await CryptoAnalysisGraph(demo_mode=True).arun("BTC")
    assert result.status == "demo"
    assert result.recommendation is None
    ask.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_api_rejects_running_event_loop():
    with pytest.raises(RuntimeError, match="await agent.arun"):
        CryptoAnalysisGraph().run("BTC")


@pytest.mark.parametrize("provider", ["openai", "anthropic", "deepseek", "gemini"])
def test_all_providers_use_spoon_chatbot(provider):
    settings = ModelSettings.from_env(provider)
    bot = create_chatbot(settings)
    assert isinstance(bot, ChatBot)
    assert bot.llm_provider == provider
    assert bot.model_name == settings.model


def test_bad_configuration_fails_early(monkeypatch):
    with pytest.raises(ValueError, match="Unsupported"):
        CryptoReActAgent(llm_provider="unknown")
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        CryptoAnalysisGraph()


@pytest.mark.asyncio
async def test_model_binding_and_provider_instances_are_isolated(monkeypatch):
    calls = []

    async def provider_operation(self, provider_name, operation, *args, **kwargs):
        calls.append(kwargs["model"])
        return LLMResponse(
            content="answer",
            provider=provider_name,
            model=kwargs["model"],
            finish_reason="stop",
            native_finish_reason="stop",
        )

    monkeypatch.setattr(LLMManager, "_execute_provider_operation", provider_operation)
    first = create_chatbot(ModelSettings.from_env("openai", "model-a"))
    second = create_chatbot(ModelSettings.from_env("openai", "model-b"))
    assert first.llm_manager.registry is not second.llm_manager.registry
    try:
        assert await first.ask([{"role": "user", "content": "hello"}]) == "answer"
        assert await second.ask([{"role": "user", "content": "hello"}]) == "answer"
        assert calls == ["model-a", "model-b"]
    finally:
        await first.llm_manager.cleanup()
        await second.llm_manager.cleanup()


@pytest.mark.asyncio
async def test_notification_failure_keeps_validated_report(graph_sources, monkeypatch):
    graph = CryptoAnalysisGraph(notify=True)
    monkeypatch.setattr(graph.notification_tool, "run", lambda **kwargs: {"success": False})
    result = await graph.arun("BTC")
    assert result.status == "completed"
    assert result.model_report is not None
    assert result.events[-1]["node"] == "notification"
    assert result.events[-1]["status"] == "failed"
    assert graph_sources.await_count == 1


def test_keyless_graph_demo(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    assert CryptoAnalysisGraph(demo_mode=True).run("BTC").status == "demo"
