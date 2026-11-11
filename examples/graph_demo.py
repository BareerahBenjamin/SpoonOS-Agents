"""
Graph Agent Demo
Demonstrates workflow orchestration with state graph
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agents.graph_agent import CryptoAnalysisGraph

# Load environment variables
load_dotenv()

console = Console()


def main():
    """Run Graph Agent demo"""

    console.print(
        Panel(
            """
[bold cyan]🥄 SpoonOS Graph Agent Demo[/bold cyan]

This demo showcases a Graph Agent with multi-step workflow:

[yellow]Workflow Steps:[/yellow]
1. 📊 Data Collection - Gather price and market data
2. 📈 Technical Analysis - Calculate indicators and trends
3. 📰 News Evidence - Retrieve source articles without fabricated sentiment
4. 🤔 Decision Generation - Create investment recommendation
5. 📢 Notification - Send results

Each step processes data and passes it to the next node.
        """,
            title="Welcome",
            border_style="cyan bold",
        )
    )

    # Get LLM configuration
    console.print("\n[yellow]Configuration:[/yellow]")

    llm_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    model_name = os.getenv("DEFAULT_MODEL_NAME") or None

    console.print(f"  LLM Provider: [green]{llm_provider}[/green]")
    console.print(f"  Model: [green]{model_name or 'provider default'}[/green]")

    # Check API keys
    if (
        llm_provider == "openai"
        and not os.getenv("OPENAI_API_KEY")
        and os.getenv("DEMO_MODE", "false").lower() != "true"
    ):
        console.print("\n[red]⚠️ OPENAI_API_KEY not found in environment![/red]")
        console.print("Please set it in your .env file or environment variables.")
        return

    # Initialize graph agent
    console.print("\n[cyan]Initializing Graph Agent...[/cyan]")

    try:
        agent = CryptoAnalysisGraph(llm_provider=llm_provider, model_name=model_name, verbose=True)
        console.print("[green]✓ Graph Agent initialized successfully![/green]\n")
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        return

    # Example cryptocurrencies
    example_cryptos = [
        ("BTC", "Bitcoin"),
        ("ETH", "Ethereum"),
        ("SOL", "Solana"),
        ("BNB", "Binance Coin"),
        ("ADA", "Cardano"),
    ]

    console.print("[yellow]Available cryptocurrencies:[/yellow]")
    for symbol, name in example_cryptos:
        console.print(f"  • {symbol} - {name}")

    console.print("\n" + "=" * 80 + "\n")

    # Interactive loop
    while True:
        try:
            # Get cryptocurrency symbol
            symbol = Prompt.ask(
                "\n[bold cyan]Enter cryptocurrency symbol[/bold cyan]", default="BTC"
            ).upper()

            if symbol.lower() in ["exit", "quit", "q"]:
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break

            # Run graph workflow
            console.print(f"\n[cyan]Starting analysis workflow for {symbol}...[/cyan]\n")
            console.print("=" * 80 + "\n")

            result = agent.run(symbol=symbol, action="analyze")

            # Display results summary
            console.print("\n" + "=" * 80 + "\n")
            display_results(result)

            # Ask if user wants to continue
            console.print("\n" + "=" * 80 + "\n")
            continue_prompt = Prompt.ask(
                "[yellow]Analyze another cryptocurrency?[/yellow]", choices=["y", "n"], default="y"
            )

            if continue_prompt.lower() == "n":
                console.print("\n[yellow]Thanks for trying the Graph Agent! 🎉[/yellow]")
                break

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Demo interrupted. Goodbye! 👋[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            console.print("[yellow]Let's try another cryptocurrency...[/yellow]")


def display_results(result):
    """Display analysis results in a nice format"""

    console.print(
        Panel(
            f"[bold]{result.symbol}[/bold] Research: {result.status}",
            title="📊 Results Summary",
            border_style="green bold",
        )
    )

    # Recommendation table
    table = Table(title="Investment Recommendation", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green bold")

    table.add_row("Status", result.status)
    table.add_row("Recommendation", result.recommendation or "Unavailable")
    table.add_row("24h rule signal", result.rule_signal or "Unavailable")
    table.add_row("Snapshot", result.snapshot_id)

    console.print(table)

    # Price data
    if result.data.get("price_data"):
        price_data = result.data["price_data"]
        console.print("\n[cyan]Price Data:[/cyan]")

        price_table = Table(show_header=False)
        price_table.add_column("Metric", style="cyan")
        price_table.add_column("Value", style="white")

        if price_data.get("current_price") is not None:
            price_table.add_row("Current Price", f"${price_data['current_price']:,.2f}")
        if price_data.get("price_change_percentage_24h") is not None:
            change = price_data["price_change_percentage_24h"]
            color = "green" if change > 0 else "red"
            price_table.add_row("24h Change", f"[{color}]{change:+.2f}%[/{color}]")
        if price_data.get("market_cap_rank") is not None:
            price_table.add_row("Market Cap Rank", f"#{price_data['market_cap_rank']}")

        console.print(price_table)

    # Technical indicators
    if result.data.get("technical_indicators"):
        indicators = result.data["technical_indicators"]
        console.print("\n[yellow]Technical Analysis:[/yellow]")

        tech_table = Table(show_header=False)
        tech_table.add_column("Indicator", style="yellow")
        tech_table.add_column("Value", style="white")

        tech_table.add_row("Data status", indicators["status"])
        if indicators.get("rsi") is not None:
            tech_table.add_row("Wilder RSI (14)", f"{indicators['rsi']:.2f}")
        for name, value in indicators.get("moving_averages", {}).items():
            tech_table.add_row(
                name, f"{value:,.2f}" if value is not None else "Insufficient samples"
            )
        if indicators.get("macd"):
            tech_table.add_row("MACD histogram", f"{indicators['macd']['histogram']:.4f}")

        console.print(tech_table)

    # Reasoning
    if result.reasoning:
        console.print("\n[magenta]Report / data limitations:[/magenta]")
        console.print(Panel(result.reasoning, border_style="magenta"))


def run_batch_demo():
    """Run batch demo with multiple cryptocurrencies"""

    console.print(
        Panel(
            "[bold cyan]Running Batch Demo[/bold cyan]\n"
            "Analyzing multiple cryptocurrencies automatically...",
            border_style="cyan",
        )
    )

    # Initialize agent
    agent = CryptoAnalysisGraph(
        llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        model_name=os.getenv("DEFAULT_MODEL_NAME") or None,
        verbose=True,
    )

    # Cryptocurrencies to analyze
    cryptos = ["BTC", "ETH", "SOL"]

    for i, symbol in enumerate(cryptos, 1):
        console.print(f"\n\n{'=' * 80}")
        console.print(f"[bold cyan]Analysis {i}/{len(cryptos)}: {symbol}[/bold cyan]")
        console.print(f"{'=' * 80}\n")

        result = agent.run(symbol=symbol, action="analyze")
        display_results(result)

        console.print(f"\n{symbol} research status: {result.status}")

    console.print(f"\n\n{'=' * 80}")
    console.print("[green bold]✓ Batch demo completed![/green bold]")
    console.print(f"{'=' * 80}\n")


def compare_demo():
    """Run comparison demo"""

    console.print(
        Panel(
            "[bold cyan]Comparison Demo[/bold cyan]\n"
            "Compare multiple cryptocurrencies side-by-side",
            border_style="cyan",
        )
    )

    # Get symbols to compare
    symbols_input = Prompt.ask(
        "[cyan]Enter symbols to compare (comma-separated)[/cyan]", default="BTC,ETH,SOL"
    )

    symbols = [s.strip().upper() for s in symbols_input.split(",")]

    # Initialize agent
    agent = CryptoAnalysisGraph(
        llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        model_name=os.getenv("DEFAULT_MODEL_NAME") or None,
        verbose=False,  # Less verbose for comparison
    )

    # Analyze all
    results = []
    for symbol in symbols:
        console.print(f"\n[cyan]Analyzing {symbol}...[/cyan]")
        result = agent.run(symbol=symbol, action="analyze")
        results.append(result)

    # Display comparison table
    console.print("\n" + "=" * 80 + "\n")
    comparison_table = Table(title="Cryptocurrency Comparison", show_header=True)
    comparison_table.add_column("Symbol", style="cyan bold")
    comparison_table.add_column("Recommendation", style="white")
    comparison_table.add_column("Signal", style="white")
    comparison_table.add_column("Status", style="white")

    for result in results:
        signal = result.rule_signal or "N/A"

        signal_color = "green" if signal == "BUY" else "red" if signal == "SELL" else "yellow"

        comparison_table.add_row(
            result.symbol,
            result.recommendation or result.status,
            f"[{signal_color}]{signal}[/{signal_color}]",
            result.status,
        )

    console.print(comparison_table)
    console.print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Graph Agent Demo")
    parser.add_argument(
        "--batch", action="store_true", help="Run batch demo with multiple cryptocurrencies"
    )
    parser.add_argument("--compare", action="store_true", help="Run comparison demo")

    args = parser.parse_args()

    if args.batch:
        run_batch_demo()
    elif args.compare:
        compare_demo()
    else:
        main()
