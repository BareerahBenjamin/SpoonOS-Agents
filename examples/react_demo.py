"""
ReAct Agent Demo
Demonstrates the reasoning-action loop for crypto Q&A
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

from agents.react_agent import CryptoReActAgent

# Load environment variables
load_dotenv()

console = Console()


def main():
    """Run ReAct Agent demo"""

    console.print(Panel(
        """
[bold cyan]🥄 SpoonOS ReAct Agent Demo[/bold cyan]

This demo showcases a ReAct (Reasoning + Acting) Agent that can:
- Answer questions about cryptocurrencies
- Search for information on the web
- Retrieve real-time price data
- Analyze market trends

The agent will show its thinking process step-by-step.
        """,
        title="Welcome",
        border_style="cyan bold"
    ))

    # Get LLM configuration
    console.print("\n[yellow]Configuration:[/yellow]")

    llm_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    model_name = os.getenv("DEFAULT_MODEL_NAME", "gpt-4-turbo-preview")

    console.print(f"  LLM Provider: [green]{llm_provider}[/green]")
    console.print(f"  Model: [green]{model_name}[/green]")

    # Check API keys
    if llm_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        console.print("\n[red]⚠️ OPENAI_API_KEY not found in environment![/red]")
        console.print("Please set it in your .env file or environment variables.")
        return

    # Initialize agent
    console.print("\n[cyan]Initializing ReAct Agent...[/cyan]")

    try:
        agent = CryptoReActAgent(
            llm_provider=llm_provider,
            model_name=model_name,
            max_iterations=10,
            verbose=True
        )
        console.print("[green]✓ Agent initialized successfully![/green]\n")
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        return

    # Example questions
    example_questions = [
        "What is the current price of Bitcoin?",
        "Compare the prices of Bitcoin and Ethereum",
        "What is the market cap rank of Solana?",
        "Tell me about recent news for BTC",
        "What are the 24h price changes for BTC and ETH?",
    ]

    console.print("[yellow]Example questions you can ask:[/yellow]")
    for i, q in enumerate(example_questions, 1):
        console.print(f"  {i}. {q}")

    console.print("\n" + "=" * 80 + "\n")

    # Interactive loop
    while True:
        try:
            # Get user question
            question = Prompt.ask(
                "\n[bold cyan]Your question[/bold cyan]",
                default="What is the current price of Bitcoin?"
            )

            if question.lower() in ["exit", "quit", "q"]:
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break

            # Run agent
            console.print("\n" + "=" * 80 + "\n")
            result = agent.run(question)

            # Ask if user wants to continue
            console.print("\n" + "=" * 80 + "\n")
            continue_prompt = Prompt.ask(
                "[yellow]Ask another question?[/yellow]",
                choices=["y", "n"],
                default="y"
            )

            if continue_prompt.lower() == "n":
                console.print("\n[yellow]Thanks for trying the ReAct Agent! 🎉[/yellow]")
                break

            # Reset agent for next question
            agent.reset()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Demo interrupted. Goodbye! 👋[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            console.print("[yellow]Let's try another question...[/yellow]")


def run_batch_demo():
    """Run batch demo with predefined questions"""

    console.print(Panel(
        "[bold cyan]Running Batch Demo[/bold cyan]\n"
        "Testing multiple questions automatically...",
        border_style="cyan"
    ))

    # Initialize agent
    agent = CryptoReActAgent(
        llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        model_name=os.getenv("DEFAULT_MODEL_NAME", "gpt-4-turbo-preview"),
        max_iterations=10,
        verbose=True
    )

    # Test questions
    questions = [
        "What is the current price of Bitcoin?",
        "Compare Bitcoin and Ethereum prices",
        "What is the market cap of Solana?",
    ]

    for i, question in enumerate(questions, 1):
        console.print(f"\n\n{'=' * 80}")
        console.print(f"[bold cyan]Question {i}/{len(questions)}[/bold cyan]")
        console.print(f"{'=' * 80}\n")

        result = agent.run(question)
        agent.reset()

    console.print(f"\n\n{'=' * 80}")
    console.print("[green bold]✓ Batch demo completed![/green bold]")
    console.print(f"{'=' * 80}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ReAct Agent Demo")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch demo with predefined questions"
    )

    args = parser.parse_args()

    if args.batch:
        run_batch_demo()
    else:
        main()
