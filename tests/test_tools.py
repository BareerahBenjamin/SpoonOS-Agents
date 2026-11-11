from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import requests
from pydantic import ValidationError
from spoon_ai.tools import ToolManager
from spoon_ai.tools.base import BaseTool

from tools.base import utc_now
from tools.crypto_tools import (
    CryptoHistoryTool,
    CryptoIndicatorTool,
    CryptoNewsTool,
    CryptoPriceTool,
    calculate_indicators,
)
from tools.notification_tools import NotificationTool
from tools.search_tools import TavilySearchTool


def response(data):
    return Mock(json=Mock(return_value=data), raise_for_status=Mock())


def price_payload():
    return {
        "name": "Bitcoin",
        "last_updated": utc_now(),
        "market_data": {
            "current_price": {"usd": 68000},
            "price_change_percentage_24h": 1.5,
        },
    }


@pytest.mark.asyncio
async def test_tools_registered_in_real_spoon_manager():
    tools = [
        CryptoPriceTool(demo_mode=True),
        CryptoNewsTool(demo_mode=True),
        CryptoHistoryTool(demo_mode=True),
        CryptoIndicatorTool(demo_mode=True),
        TavilySearchTool(demo_mode=True),
    ]
    assert all(isinstance(tool, BaseTool) for tool in tools)
    manager = ToolManager(tools)
    result = await manager.execute(name="get_crypto_price", tool_input={"symbol": "btc"})
    assert result["status"] == "mock"
    assert result["symbol"] == "BTC"
    assert manager.to_params()[0]["function"]["parameters"]["required"] == ["symbol"]


def test_price_http_failure_never_falls_back(monkeypatch):
    request = Mock(side_effect=requests.Timeout("includes-secret-url"))
    monkeypatch.setattr(requests, "request", request)
    result = CryptoPriceTool().run(symbol="BTC")
    assert result["status"] == "unavailable"
    assert "current_price" not in result
    assert "secret" not in str(result)
    assert request.call_count == 2


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"market_data": {"current_price": {"usd": 0}}},
        {"market_data": {"current_price": {"usd": float("nan")}}},
    ],
)
def test_invalid_price_is_unavailable(monkeypatch, payload):
    monkeypatch.setattr(requests, "request", Mock(return_value=response(payload)))
    assert CryptoPriceTool().run(symbol="BTC")["status"] == "unavailable"


@pytest.mark.parametrize(
    "plan,domain,header",
    [
        ("demo", "api.coingecko.com", "x-cg-demo-api-key"),
        ("pro", "pro-api.coingecko.com", "x-cg-pro-api-key"),
    ],
)
def test_coingecko_plan_matches_auth(monkeypatch, plan, domain, header):
    monkeypatch.setenv("COINGECKO_PLAN", plan)
    monkeypatch.setenv("COINGECKO_API_KEY", "test-key")
    request = Mock(return_value=response(price_payload()))
    monkeypatch.setattr(requests, "request", request)
    result = CryptoPriceTool().run(symbol="btc")
    assert result["status"] == "live"
    assert result["current_price"] == 68000
    assert domain in request.call_args.args[1]
    assert request.call_args.kwargs["headers"] == {header: "test-key"}
    assert result["total_volume"] is None
    assert result["updated_at"] is not None


def test_missing_tavily_key_is_visible():
    assert TavilySearchTool().run(query="BTC")["status"] == "unavailable"
    assert CryptoNewsTool().run(symbol="BTC")["articles"] == []


def test_news_uses_real_sources_deduplicates_and_keeps_unknown_dates(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    row = {"title": "BTC evidence", "url": "https://source.example/story", "content": "Facts"}
    request = Mock(return_value=response({"results": [row, row, {**row, "url": "javascript:bad"}]}))
    monkeypatch.setattr(requests, "request", request)
    result = CryptoNewsTool().run(symbol="BTC", limit=3)
    assert result["status"] == "live"
    assert result["article_count"] == 1
    assert result["articles"][0]["published_at"] is None
    assert request.call_args.kwargs["json"]["topic"] == "news"


def test_empty_or_failed_search_is_unavailable(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(requests, "request", Mock(return_value=response({"results": []})))
    assert TavilySearchTool().run(query="BTC")["status"] == "unavailable"


@pytest.mark.parametrize(
    "tool,args",
    [
        (CryptoPriceTool, {"symbol": "../BTC"}),
        (CryptoNewsTool, {"symbol": "BTC", "limit": -1}),
        (TavilySearchTool, {"query": "", "max_results": 5}),
        (TavilySearchTool, {"query": "BTC", "max_results": 100}),
        (CryptoHistoryTool, {"symbol": "BTC", "days": 1}),
        (CryptoIndicatorTool, {"symbol": "BTC", "timeframe": "1h"}),
    ],
)
def test_invalid_tool_arguments_fail_before_http(tool, args):
    with pytest.raises(ValidationError):
        tool().run(**args)


@pytest.mark.parametrize("slope,rsi", [(1, 100), (-1, 0), (0, 50)])
def test_real_indicator_math(slope, rsi):
    history = {
        "status": "live",
        "source": "fixture",
        "prices": [[i * 86400000, 500 + i * slope] for i in range(120)],
    }
    result = calculate_indicators(history)
    assert result["rsi"] == rsi
    assert result["moving_averages"]["ma_7"] == pytest.approx(500 + slope * 116)
    assert result["macd"]["macd_line"] == pytest.approx(7 * slope)
    assert result["macd"]["histogram"] == pytest.approx(0, abs=1e-10)


def test_missing_history_cannot_produce_indicators():
    result = calculate_indicators({"status": "unavailable", "prices": []})
    assert result["status"] == "unavailable"
    assert "rsi" not in result


def test_stale_price_is_explicitly_unavailable(monkeypatch):
    data = price_payload()
    data["last_updated"] = "2020-01-01T00:00:00Z"
    monkeypatch.setattr(requests, "request", Mock(return_value=response(data)))
    result = CryptoPriceTool().run(symbol="BTC")
    assert result["status"] == "unavailable"
    assert "stale" in result["error"]


def test_history_uses_daily_samples_and_discards_partial_day(monkeypatch):
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = int(midnight.timestamp() * 1000)
    prices = [[end - (119 - i) * 86400000, 100 + i] for i in range(120)]
    prices.append([end + 3600000, 99999])
    monkeypatch.setattr(requests, "request", Mock(return_value=response({"prices": prices})))
    result = CryptoHistoryTool().run(symbol="BTC")
    assert result["status"] == "live"
    assert len(result["prices"]) == 120
    assert result["prices"][-1][1] == 219


def test_pro_plan_without_key_fails_at_initialization(monkeypatch):
    monkeypatch.setenv("COINGECKO_PLAN", "pro")
    with pytest.raises(ValueError, match="COINGECKO_API_KEY"):
        CryptoPriceTool()


def test_notification_console():
    assert NotificationTool().run(message="Test", channel="console")["success"] is True
