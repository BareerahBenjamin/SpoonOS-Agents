"""
Tests for tools
"""

import pytest
from tools.crypto_tools import CryptoPriceTool, CryptoNewsTool
from tools.search_tools import TavilySearchTool
from tools.notification_tools import NotificationTool


class TestCryptoTools:
    """Test cryptocurrency tools"""

    def test_crypto_price_tool(self):
        """Test CryptoPriceTool"""
        tool = CryptoPriceTool()
        result = tool.run(symbol="BTC")

        assert isinstance(result, dict)
        assert "symbol" in result
        assert "current_price" in result
        assert result["symbol"] == "BTC"

    def test_crypto_news_tool(self):
        """Test CryptoNewsTool"""
        tool = CryptoNewsTool()
        result = tool.run(symbol="BTC", limit=3)

        assert isinstance(result, dict)
        assert "symbol" in result
        assert "articles" in result
        assert len(result["articles"]) <= 3


class TestSearchTools:
    """Test search tools"""

    def test_tavily_search_tool(self):
        """Test TavilySearchTool"""
        tool = TavilySearchTool()
        result = tool.run(query="What is Bitcoin?", max_results=3)

        assert isinstance(result, dict)
        assert "query" in result
        assert "results" in result
        assert len(result["results"]) <= 3


class TestNotificationTools:
    """Test notification tools"""

    def test_notification_tool_console(self):
        """Test NotificationTool with console channel"""
        tool = NotificationTool()
        result = tool.run(message="Test message", channel="console")

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["channel"] == "console"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
