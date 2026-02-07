"""
Cryptocurrency data tools
"""

import os
import requests
from typing import Dict, Any, Optional
from loguru import logger


class BaseTool:
    """Base class for all tools"""

    name: str = "base_tool"
    description: str = "Base tool"

    def run(self, **kwargs) -> Any:
        """Execute the tool"""
        raise NotImplementedError


class CryptoPriceTool(BaseTool):
    """Tool to get cryptocurrency price data"""

    name = "get_crypto_price"
    description = "Get current price, market cap, volume, and 24h change for a cryptocurrency. Input should be a symbol like 'BTC' or 'ETH'."

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = os.getenv("COINGECKO_API_KEY", "")

    def _get_coin_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to CoinGecko ID"""
        # Common mappings
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "ADA": "cardano",
            "XRP": "ripple",
            "DOT": "polkadot",
            "DOGE": "dogecoin",
            "AVAX": "avalanche-2",
            "MATIC": "matic-network",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "ATOM": "cosmos",
            "LTC": "litecoin",
            "BCH": "bitcoin-cash",
        }

        return symbol_map.get(symbol.upper(), symbol.lower())

    def run(self, symbol: str) -> Dict[str, Any]:
        """
        Get cryptocurrency price data

        Args:
            symbol: Cryptocurrency symbol (e.g., "BTC", "ETH")

        Returns:
            Dictionary with price data
        """
        try:
            coin_id = self._get_coin_id(symbol)

            # Call CoinGecko API
            url = f"{self.base_url}/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
            }

            headers = {}
            if self.api_key:
                headers["x-cg-pro-api-key"] = self.api_key

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extract relevant data
            market_data = data.get("market_data", {})

            result = {
                "symbol": symbol.upper(),
                "name": data.get("name", ""),
                "current_price": market_data.get("current_price", {}).get("usd", 0),
                "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                "total_volume": market_data.get("total_volume", {}).get("usd", 0),
                "price_change_24h": market_data.get("price_change_24h", 0),
                "price_change_percentage_24h": market_data.get("price_change_percentage_24h", 0),
                "market_cap_rank": market_data.get("market_cap_rank", 0),
                "high_24h": market_data.get("high_24h", {}).get("usd", 0),
                "low_24h": market_data.get("low_24h", {}).get("usd", 0),
                "ath": market_data.get("ath", {}).get("usd", 0),  # All-time high
                "atl": market_data.get("atl", {}).get("usd", 0),  # All-time low
            }

            logger.info(f"Fetched price data for {symbol}: ${result['current_price']:,.2f}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            # Return mock data for demo purposes
            return {
                "symbol": symbol.upper(),
                "name": symbol,
                "current_price": 50000 if symbol.upper() == "BTC" else 3000,
                "market_cap": 1000000000000,
                "total_volume": 50000000000,
                "price_change_24h": 500,
                "price_change_percentage_24h": 1.2,
                "market_cap_rank": 1,
                "high_24h": 51000 if symbol.upper() == "BTC" else 3100,
                "low_24h": 49000 if symbol.upper() == "BTC" else 2900,
                "ath": 69000 if symbol.upper() == "BTC" else 4800,
                "atl": 100 if symbol.upper() == "BTC" else 0.5,
                "_note": "Mock data - API error occurred"
            }


class CryptoNewsTool(BaseTool):
    """Tool to get cryptocurrency news"""

    name = "get_crypto_news"
    description = "Get latest news articles about a cryptocurrency. Input should be a symbol like 'BTC' or 'ETH'."

    def run(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get cryptocurrency news

        Args:
            symbol: Cryptocurrency symbol
            limit: Number of articles to return

        Returns:
            Dictionary with news articles
        """
        try:
            # For demo purposes, return mock news
            # In production, you would use a real news API like CryptoPanic or NewsAPI

            news_templates = [
                f"{symbol} reaches new milestone as institutional adoption grows",
                f"Analysts predict bullish trend for {symbol} in coming weeks",
                f"Major exchange lists {symbol} trading pairs",
                f"{symbol} network upgrade scheduled for next month",
                f"Whale activity detected in {symbol} markets",
            ]

            articles = [
                {
                    "title": news_templates[i % len(news_templates)],
                    "source": "CryptoNews",
                    "url": f"https://example.com/news/{i}",
                    "published_at": "2024-01-15",
                    "sentiment": "neutral",
                }
                for i in range(limit)
            ]

            logger.info(f"Fetched {len(articles)} news articles for {symbol}")

            return {
                "symbol": symbol.upper(),
                "article_count": len(articles),
                "articles": articles,
            }

        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "article_count": 0,
                "articles": [],
            }


class CryptoIndicatorTool(BaseTool):
    """Tool to calculate technical indicators"""

    name = "calculate_indicators"
    description = "Calculate technical indicators (RSI, MACD, etc.) for a cryptocurrency"

    def run(self, symbol: str, timeframe: str = "1d") -> Dict[str, Any]:
        """
        Calculate technical indicators

        Args:
            symbol: Cryptocurrency symbol
            timeframe: Timeframe for calculation (1h, 4h, 1d, etc.)

        Returns:
            Dictionary with technical indicators
        """
        try:
            # For demo purposes, return mock indicators
            # In production, you would calculate real indicators from historical data

            indicators = {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "rsi": 65.5,  # Relative Strength Index
                "macd": {
                    "macd_line": 120.5,
                    "signal_line": 115.2,
                    "histogram": 5.3,
                },
                "moving_averages": {
                    "ma_7": 50000,
                    "ma_25": 48000,
                    "ma_99": 45000,
                },
                "bollinger_bands": {
                    "upper": 52000,
                    "middle": 50000,
                    "lower": 48000,
                },
                "signals": {
                    "trend": "bullish",
                    "strength": "moderate",
                    "recommendation": "HOLD",
                },
            }

            logger.info(f"Calculated indicators for {symbol}")
            return indicators

        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {}


if __name__ == "__main__":
    # Test tools
    price_tool = CryptoPriceTool()
    print("Testing CryptoPriceTool:")
    print(price_tool.run(symbol="BTC"))

    news_tool = CryptoNewsTool()
    print("\nTesting CryptoNewsTool:")
    print(news_tool.run(symbol="BTC"))

    indicator_tool = CryptoIndicatorTool()
    print("\nTesting CryptoIndicatorTool:")
    print(indicator_tool.run(symbol="BTC"))
