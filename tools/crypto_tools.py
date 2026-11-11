"""Read-only market tools implemented with SpoonOS BaseTool."""

import math
import os
from datetime import datetime, timezone
from statistics import mean

import requests
from pydantic import Field

from tools.base import (
    AssetInput,
    DataQualityError,
    ResearchTool,
    failure_reason,
    metadata,
    request_json,
)
from tools.search_tools import TavilySearchTool

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOT": "polkadot",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "POL": "polygon-ecosystem-token",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
}


def coin_id(symbol: str) -> str:
    # Non-mapped input must be a CoinGecko asset ID, not an ambiguous ticker lookup.
    return COINS.get(symbol.upper(), symbol.lower())


def coingecko_config() -> tuple[str, dict]:
    plan = os.getenv("COINGECKO_PLAN", "demo").lower()
    if plan not in {"demo", "pro"}:
        raise ValueError("COINGECKO_PLAN must be demo or pro")
    key = os.getenv("COINGECKO_API_KEY", "")
    if "your-" in key:
        key = ""
    if plan == "pro" and not key:
        raise ValueError("COINGECKO_API_KEY is required for the pro plan")
    host = "pro-api" if plan == "pro" else "api"
    headers = {f"x-cg-{plan}-api-key": key} if key else {}
    return f"https://{host}.coingecko.com/api/v3", headers


def finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class CoinGeckoTool(ResearchTool):
    def model_post_init(self, context):
        if not self.demo_mode:
            coingecko_config()


class CryptoPriceTool(CoinGeckoTool):
    name: str = "get_crypto_price"
    description: str = "Get a USD CoinGecko snapshot with source, timestamps and availability."
    parameters: dict = AssetInput.model_json_schema()
    input_model = AssetInput

    def _get_coin_id(self, symbol: str) -> str:
        return coin_id(symbol)

    def _run(self, symbol: str) -> dict:
        asset_id = coin_id(symbol)
        base = {"symbol": symbol, "asset_id": asset_id, "currency": "usd"}
        if self.demo_mode:
            return {
                **base,
                **metadata("mock", "demo"),
                "current_price": 50000.0,
                "price_change_percentage_24h": 1.2,
                "market_cap": 1e12,
                "total_volume": 5e10,
            }
        host, headers = coingecko_config()
        url = f"{host}/coins/{asset_id}"
        try:
            data = request_json(
                "GET",
                url,
                headers=headers,
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                },
            )
            market = data["market_data"]
            price = market["current_price"]["usd"]
            if not finite_number(price) or price <= 0:
                raise DataQualityError("Missing positive USD price")
            updated = datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - updated).total_seconds()
            if not -300 <= age <= 7200:
                raise DataQualityError("Price source timestamp is stale (>2h) or in the future")
            result = {
                **base,
                **metadata("live", url, updated_at=data.get("last_updated")),
                "name": data.get("name", asset_id),
                "current_price": price,
            }
            for key in ("market_cap", "total_volume", "high_24h", "low_24h", "ath", "atl"):
                value = market.get(key, {}).get("usd")
                result[key] = value if finite_number(value) else None
            for key in ("price_change_24h", "price_change_percentage_24h", "market_cap_rank"):
                value = market.get(key)
                result[key] = value if finite_number(value) else None
            return result
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            OverflowError,
            OSError,
        ) as exc:
            return {**base, **metadata("unavailable", url, error=failure_reason(exc))}


class NewsInput(AssetInput):
    limit: int = Field(default=5, ge=1, le=10, strict=True)


class CryptoNewsTool(ResearchTool):
    name: str = "get_crypto_news"
    description: str = "Retrieve news evidence via Tavily; missing publication dates stay unknown."
    parameters: dict = NewsInput.model_json_schema()
    input_model = NewsInput

    def _run(self, symbol: str, limit: int = 5) -> dict:
        result = TavilySearchTool(demo_mode=self.demo_mode).run(
            query=f"{coin_id(symbol)} {symbol} cryptocurrency", max_results=limit, topic="news"
        )
        articles = result.pop("results")
        return {**result, "symbol": symbol, "article_count": len(articles), "articles": articles}


class HistoryInput(AssetInput):
    days: int = Field(default=120, ge=35, le=365, strict=True)


class CryptoHistoryTool(CoinGeckoTool):
    name: str = "get_crypto_history"
    description: str = "Get daily CoinGecko USD price samples for real indicator computation."
    parameters: dict = HistoryInput.model_json_schema()
    input_model = HistoryInput

    def _run(self, symbol: str, days: int = 120) -> dict:
        base = {
            "symbol": symbol,
            "asset_id": coin_id(symbol),
            "currency": "usd",
            "interval": "daily",
            "days": days,
            "prices": [],
            "total_volumes": [],
        }
        if self.demo_mode:
            return {**base, **metadata("unavailable", "demo", error="Demo history is not provided")}
        host, headers = coingecko_config()
        url = f"{host}/coins/{coin_id(symbol)}/market_chart"
        try:
            data = request_json(
                "GET",
                url,
                headers=headers,
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
            )
            prices = data["prices"]
            if not isinstance(prices, list) or len(prices) < 35:
                raise DataQualityError("Insufficient historical prices")
            previous = -1
            for timestamp, value in prices:
                if (
                    not finite_number(timestamp)
                    or timestamp <= previous
                    or not finite_number(value)
                    or value <= 0
                ):
                    raise DataQualityError("Invalid historical sample")
                previous = timestamp
            # CoinGecko appends a current partial-day point; exclude it from daily indicators.
            if prices[-1][0] - prices[-2][0] < 23 * 3600000:
                prices = prices[:-1]
            if len(prices) < 35 or any(
                not 23 * 3600000 <= b[0] - a[0] <= 25 * 3600000 for a, b in zip(prices, prices[1:])
            ):
                raise DataQualityError("History is not a complete daily sample series")
            updated_at = datetime.fromtimestamp(prices[-1][0] / 1000, timezone.utc)
            if not -300 <= (datetime.now(timezone.utc) - updated_at).total_seconds() <= 172800:
                raise DataQualityError(
                    "Historical source timestamp is stale (>48h) or in the future"
                )
            return {
                **base,
                **metadata("live", url, updated_at=updated_at.isoformat()),
                "prices": prices,
                "total_volumes": data.get("total_volumes", []),
            }
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            OverflowError,
            OSError,
        ) as exc:
            return {**base, **metadata("unavailable", url, error=failure_reason(exc))}


def calculate_indicators(history: dict) -> dict:
    """SMA, Wilder RSI(14) and SMA-seeded MACD(12,26,9) over daily samples."""
    rows = history.get("prices", [])
    if (
        history.get("status") != "live"
        or len(rows) < 35
        or any(
            not isinstance(row, (list, tuple))
            or len(row) != 2
            or not finite_number(row[1])
            or row[1] <= 0
            for row in rows
        )
    ):
        return {
            **metadata("unavailable", history.get("source", "coingecko")),
            "error": "At least 35 live daily price samples are required",
        }
    prices = [row[1] for row in history["prices"]]
    changes = [b - a for a, b in zip(prices, prices[1:])]
    gain = mean(max(c, 0) for c in changes[:14])
    loss = mean(max(-c, 0) for c in changes[:14])
    for change in changes[14:]:
        gain = (gain * 13 + max(change, 0)) / 14
        loss = (loss * 13 + max(-change, 0)) / 14
    rsi = 50.0 if gain == loss == 0 else 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)

    def ema(values, period):
        average = mean(values[:period])
        output = [average]
        for value in values[period:]:
            average += (value - average) * 2 / (period + 1)
            output.append(average)
        return output

    fast, slow = ema(prices, 12), ema(prices, 26)
    macd = [a - b for a, b in zip(fast[14:], slow)]
    signal = ema(macd, 9)[-1]
    return {
        **metadata("live", history["source"], updated_at=history.get("updated_at")),
        "method": "daily price samples; Wilder RSI14; SMA-seeded MACD12/26/9",
        "sample_count": len(prices),
        "rsi": rsi,
        "moving_averages": {
            f"ma_{n}": mean(prices[-n:]) if len(prices) >= n else None for n in (7, 25, 99)
        },
        "macd": {"macd_line": macd[-1], "signal_line": signal, "histogram": macd[-1] - signal},
    }


class IndicatorInput(AssetInput):
    timeframe: str = Field(default="1d", pattern=r"^1d$")


class CryptoIndicatorTool(CoinGeckoTool):
    name: str = "calculate_indicators"
    description: str = "Calculate daily RSI, MACD and moving averages from real historical samples."
    parameters: dict = IndicatorInput.model_json_schema()
    input_model = IndicatorInput

    def _run(self, symbol: str, timeframe: str = "1d") -> dict:
        history = CryptoHistoryTool(demo_mode=self.demo_mode).run(symbol=symbol)
        return {"symbol": symbol, "timeframe": timeframe, **calculate_indicators(history)}
