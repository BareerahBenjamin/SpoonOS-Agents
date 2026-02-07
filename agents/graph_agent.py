"""
Graph Agent Implementation
Uses state graph for complex workflow orchestration
"""

import os
from typing import TypedDict, Annotated, Sequence
from dataclasses import dataclass
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
except ImportError:
    logger.warning("LangGraph not installed. Graph agent features will be limited.")
    StateGraph = None

console = Console()


class AgentState(TypedDict):
    """State for the crypto analysis graph"""
    symbol: str
    action: str
    price_data: dict
    technical_indicators: dict
    sentiment_data: dict
    analysis_result: str
    decision: str
    messages: Sequence[BaseMessage]


@dataclass
class AnalysisResult:
    """Result of the crypto analysis"""
    symbol: str
    recommendation: str
    confidence: float
    reasoning: str
    data: dict


class CryptoAnalysisGraph:
    """
    Graph Agent for cryptocurrency analysis workflow

    Workflow:
    1. Collect Data → Gather price, volume, and market data
    2. Technical Analysis → Calculate technical indicators
    3. Sentiment Analysis → Analyze news and social media
    4. Generate Decision → Combine all data to make recommendation
    5. Send Notification → Alert user with results
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        model_name: str = "gpt-4-turbo-preview",
        verbose: bool = True
    ):
        """
        Initialize the Graph Agent

        Args:
            llm_provider: LLM provider to use
            model_name: Model name to use
            verbose: Whether to print intermediate steps
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.verbose = verbose

        # Initialize LLM
        self._init_llm()

        # Initialize tools
        self._init_tools()

        # Build graph
        self.graph = self._build_graph()

        logger.info("Initialized Graph Agent with crypto analysis workflow")

    def _init_llm(self):
        """Initialize the LLM"""
        if self.llm_provider == "openai":
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.llm_provider == "anthropic":
            from anthropic import Anthropic
            self.llm_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif self.llm_provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.llm_client = genai.GenerativeModel(self.model_name)

    def _init_tools(self):
        """Initialize tools"""
        from tools.crypto_tools import CryptoPriceTool, CryptoNewsTool
        from tools.notification_tools import NotificationTool

        self.price_tool = CryptoPriceTool()
        self.news_tool = CryptoNewsTool()
        self.notification_tool = NotificationTool()

    # ==================== Graph Nodes ====================

    def collect_data_node(self, state: AgentState) -> AgentState:
        """Node 1: Collect price and market data"""
        if self.verbose:
            console.print(Panel(
                f"[cyan]Collecting data for {state['symbol']}...[/cyan]",
                title="📊 Data Collection",
                border_style="cyan"
            ))

        symbol = state["symbol"]

        # Get price data
        try:
            price_data = self.price_tool.run(symbol=symbol)
            state["price_data"] = price_data

            if self.verbose:
                table = Table(title=f"{symbol} Price Data")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                for key, value in price_data.items():
                    table.add_row(str(key), str(value))

                console.print(table)

        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            state["price_data"] = {}

        return state

    def technical_analysis_node(self, state: AgentState) -> AgentState:
        """Node 2: Perform technical analysis"""
        if self.verbose:
            console.print(Panel(
                "[yellow]Calculating technical indicators...[/yellow]",
                title="📈 Technical Analysis",
                border_style="yellow"
            ))

        price_data = state.get("price_data", {})

        # Calculate simple indicators
        indicators = {}

        try:
            current_price = price_data.get("current_price", 0)
            price_change_24h = price_data.get("price_change_percentage_24h", 0)
            volume_24h = price_data.get("total_volume", 0)

            # Simple trend analysis
            if price_change_24h > 5:
                indicators["trend"] = "Strong Uptrend"
                indicators["signal"] = "BUY"
            elif price_change_24h > 0:
                indicators["trend"] = "Uptrend"
                indicators["signal"] = "HOLD"
            elif price_change_24h > -5:
                indicators["trend"] = "Downtrend"
                indicators["signal"] = "HOLD"
            else:
                indicators["trend"] = "Strong Downtrend"
                indicators["signal"] = "SELL"

            # Volume analysis
            indicators["volume_status"] = "High" if volume_24h > 1e9 else "Normal"

            state["technical_indicators"] = indicators

            if self.verbose:
                table = Table(title="Technical Indicators")
                table.add_column("Indicator", style="yellow")
                table.add_column("Value", style="green")

                for key, value in indicators.items():
                    table.add_row(str(key), str(value))

                console.print(table)

        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            state["technical_indicators"] = {}

        return state

    def sentiment_analysis_node(self, state: AgentState) -> AgentState:
        """Node 3: Analyze sentiment from news"""
        if self.verbose:
            console.print(Panel(
                "[magenta]Analyzing market sentiment...[/magenta]",
                title="📰 Sentiment Analysis",
                border_style="magenta"
            ))

        symbol = state["symbol"]

        try:
            # Get news
            news_data = self.news_tool.run(symbol=symbol)

            # Simple sentiment scoring
            sentiment = {
                "news_count": len(news_data.get("articles", [])),
                "overall_sentiment": "Neutral",  # Simplified
                "news_headlines": [
                    article.get("title", "")
                    for article in news_data.get("articles", [])[:3]
                ]
            }

            state["sentiment_data"] = sentiment

            if self.verbose:
                console.print(Panel(
                    f"Found {sentiment['news_count']} news articles\n"
                    f"Overall Sentiment: {sentiment['overall_sentiment']}",
                    border_style="magenta"
                ))

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            state["sentiment_data"] = {}

        return state

    def generate_decision_node(self, state: AgentState) -> AgentState:
        """Node 4: Generate investment decision using LLM"""
        if self.verbose:
            console.print(Panel(
                "[blue]Generating investment decision...[/blue]",
                title="🤔 Decision Generation",
                border_style="blue"
            ))

        # Prepare context for LLM
        context = f"""
Analyze the following cryptocurrency data and provide an investment recommendation:

Symbol: {state['symbol']}

Price Data:
{state.get('price_data', {})}

Technical Indicators:
{state.get('technical_indicators', {})}

Sentiment Data:
{state.get('sentiment_data', {})}

Provide a clear recommendation (BUY/HOLD/SELL) with reasoning and confidence level (0-100%).
Format your response as JSON:
{{
    "recommendation": "BUY/HOLD/SELL",
    "confidence": 85,
    "reasoning": "Your detailed reasoning here"
}}
"""

        try:
            if self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": context}],
                    temperature=0.3,
                )
                decision_text = response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                response = self.llm_client.messages.create(
                    model=self.model_name,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": context}],
                    temperature=0.3,
                )
                decision_text = response.content[0].text

            elif self.llm_provider == "gemini":
                response = self.llm_client.generate_content(
                    context,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 1000,
                    }
                )
                decision_text = response.text

            state["decision"] = decision_text

            if self.verbose:
                console.print(Panel(
                    decision_text,
                    title="💡 Investment Decision",
                    border_style="green bold"
                ))

        except Exception as e:
            logger.error(f"Error generating decision: {e}")
            state["decision"] = "Error generating decision"

        return state

    def notification_node(self, state: AgentState) -> AgentState:
        """Node 5: Send notification with results"""
        if self.verbose:
            console.print(Panel(
                "[green]Sending notification...[/green]",
                title="📧 Notification",
                border_style="green"
            ))

        try:
            message = f"""
Crypto Analysis Complete: {state['symbol']}

Decision: {state.get('decision', 'N/A')}

Technical Signal: {state.get('technical_indicators', {}).get('signal', 'N/A')}
Trend: {state.get('technical_indicators', {}).get('trend', 'N/A')}

This is an automated analysis. Always do your own research before investing.
"""

            # Send notification
            self.notification_tool.run(message=message, channel="console")

            if self.verbose:
                console.print("[green]✓ Notification sent successfully[/green]")

        except Exception as e:
            logger.error(f"Error sending notification: {e}")

        return state

    # ==================== Graph Construction ====================

    def _build_graph(self):
        """Build the state graph"""
        if StateGraph is None:
            logger.warning("LangGraph not available. Using simplified workflow.")
            return None

        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("collect_data", self.collect_data_node)
        workflow.add_node("technical_analysis", self.technical_analysis_node)
        workflow.add_node("sentiment_analysis", self.sentiment_analysis_node)
        workflow.add_node("generate_decision", self.generate_decision_node)
        workflow.add_node("notification", self.notification_node)

        # Add edges (define workflow)
        workflow.set_entry_point("collect_data")
        workflow.add_edge("collect_data", "technical_analysis")
        workflow.add_edge("technical_analysis", "sentiment_analysis")
        workflow.add_edge("sentiment_analysis", "generate_decision")
        workflow.add_edge("generate_decision", "notification")
        workflow.add_edge("notification", END)

        # Compile graph
        return workflow.compile()

    # ==================== Execution ====================

    def run(self, symbol: str, action: str = "analyze") -> AnalysisResult:
        """
        Run the graph workflow

        Args:
            symbol: Cryptocurrency symbol (e.g., "BTC", "ETH")
            action: Action to perform (default: "analyze")

        Returns:
            Analysis result
        """
        console.print(Panel(
            f"[bold]Starting analysis for {symbol}[/bold]",
            title="🚀 Graph Agent",
            border_style="blue bold"
        ))

        # Initialize state
        initial_state: AgentState = {
            "symbol": symbol,
            "action": action,
            "price_data": {},
            "technical_indicators": {},
            "sentiment_data": {},
            "analysis_result": "",
            "decision": "",
            "messages": [],
        }

        if self.graph:
            # Run graph
            final_state = self.graph.invoke(initial_state)
        else:
            # Fallback: run nodes sequentially
            state = initial_state
            state = self.collect_data_node(state)
            state = self.technical_analysis_node(state)
            state = self.sentiment_analysis_node(state)
            state = self.generate_decision_node(state)
            state = self.notification_node(state)
            final_state = state

        # Create result
        result = AnalysisResult(
            symbol=symbol,
            recommendation=final_state.get("technical_indicators", {}).get("signal", "HOLD"),
            confidence=0.75,  # Simplified
            reasoning=final_state.get("decision", ""),
            data={
                "price_data": final_state.get("price_data", {}),
                "technical_indicators": final_state.get("technical_indicators", {}),
                "sentiment_data": final_state.get("sentiment_data", {}),
            }
        )

        return result


if __name__ == "__main__":
    # Example usage
    agent = CryptoAnalysisGraph(
        llm_provider="openai",
        model_name="gpt-4-turbo-preview"
    )

    result = agent.run(symbol="BTC", action="analyze")
    print(f"\nAnalysis complete: {result.recommendation}")
