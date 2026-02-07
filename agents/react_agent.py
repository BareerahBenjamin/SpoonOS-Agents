"""
ReAct Agent Implementation
Combines Reasoning and Acting in an iterative loop
"""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown


console = Console()


@dataclass
class AgentStep:
    """Represents a single step in the ReAct loop"""
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class CryptoReActAgent:
    """
    ReAct Agent for cryptocurrency analysis and Q&A

    The agent follows this loop:
    1. Thought: Reason about what to do next
    2. Action: Select and execute a tool
    3. Observation: Observe the result
    4. Repeat until final answer is ready
    """

    REACT_PROMPT_TEMPLATE = """You are a cryptocurrency analysis assistant with access to various tools.

Available Tools:
{tools}

Use the following format:

Thought: Think about what information you need
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (JSON format)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original question

Begin!

Question: {question}
{history}
Thought:"""

    def __init__(
        self,
        llm_provider: str = "gemini",
        model_name: str = "gemini-2.5-flash",
        max_iterations: int = 10,
        verbose: bool = True,
	    proxy: str = None
    ):
        """
        Initialize the ReAct Agent
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.history: List[AgentStep] = []
        self.proxy = proxy

        # Initialize LLM
        self._init_llm()

        # Initialize tools
        self.tools = self._init_tools()

        logger.info(f"Initialized ReAct Agent with {llm_provider}/{model_name}")

    def _init_llm(self):
        """Initialize the LLM based on provider"""
        if self.llm_provider == "openai":
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
        elif self.llm_provider == "gemini":
            # 必须使用这个导入
            import google.generativeai as genai
            
            # 核心修复 1: 确保从环境变量读取 Key
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.error("GEMINI_API_KEY not found in environment variables!")
            
            # 核心修复 2: 强制使用 transport="rest"
            # 只有开启这个，SDK 才会走你设置的 http_proxy 环境变量
            genai.configure(
                api_key=api_key,
                transport="rest"
            )
            
            self.llm_client = genai.GenerativeModel(self.model_name)
            logger.success("Gemini client initialized with REST transport (Proxy compatible).")
            
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    def _init_tools(self) -> Dict[str, Any]:
        """Initialize available tools"""
        # 注意：此处确保你的 tools 目录下有对应的实现文件
        from tools.search_tools import TavilySearchTool
        from tools.crypto_tools import CryptoPriceTool, CryptoNewsTool

        tools = {
            "search": TavilySearchTool(),
            "get_crypto_price": CryptoPriceTool(),
            "get_crypto_news": CryptoNewsTool(),
        }

        return tools

    def _format_tools(self) -> str:
        """Format tool descriptions for the prompt"""
        tool_descriptions = []
        for name, tool in self.tools.items():
            tool_descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(tool_descriptions)

    def _format_history(self) -> str:
        """Format conversation history"""
        if not self.history:
            return ""

        history_text = []
        for step in self.history:
            history_text.append(f"Thought: {step.thought}")
            if step.action:
                history_text.append(f"Action: {step.action}")
                history_text.append(f"Action Input: {json.dumps(step.action_input)}")
            if step.observation:
                history_text.append(f"Observation: {step.observation}")

        return "\n".join(history_text)

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt"""
        if self.llm_provider == "openai":
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content

        elif self.llm_provider == "anthropic":
            response = self.llm_client.messages.create(
                model=self.model_name,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.content[0].text

        elif self.llm_provider == "gemini":
            response = self.llm_client.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 2000,
                }
            )
            return response.text

    def _parse_action(self, text: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse action and action input from LLM response"""
        lines = text.strip().split("\n")
        action = None
        action_input = None

        for i, line in enumerate(lines):
            if line.startswith("Action:"):
                action = line.split("Action:")[1].strip()
            elif line.startswith("Action Input:"):
                input_text = line.split("Action Input:")[1].strip()
                try:
                    action_input = json.loads(input_text)
                except json.JSONDecodeError:
                    action_input = {"query": input_text}

        return action, action_input

    def _execute_tool(self, action: str, action_input: Dict[str, Any]) -> str:
        """Execute a tool and return the observation"""
        if action not in self.tools:
            return f"Error: Tool '{action}' not found."

        try:
            tool = self.tools[action]
            result = tool.run(**action_input)
            return str(result)
        except Exception as e:
            logger.error(f"Error executing tool {action}: {e}")
            return f"Error executing {action}: {str(e)}"

    def _display_step(self, step: AgentStep, iteration: int):
        """Display the current step"""
        if not self.verbose:
            return

        console.print(f"\n[bold cyan]Iteration {iteration}[/bold cyan]")
        console.print(Panel(step.thought, title="💭 Thought", border_style="blue"))

        if step.action:
            console.print(Panel(
                f"[yellow]{step.action}[/yellow]\nInput: {json.dumps(step.action_input, indent=2)}",
                title="🔧 Action",
                border_style="yellow"
            ))

        if step.observation:
            console.print(Panel(step.observation, title="👁️ Observation", border_style="green"))

    def run(self, question: str) -> str:
        """Run the ReAct agent"""
        self.history = []

        console.print(Panel(f"[bold]{question}[/bold]", title="❓ Question", border_style="magenta"))

        for iteration in range(self.max_iterations):
            prompt = self.REACT_PROMPT_TEMPLATE.format(
                tools=self._format_tools(),
                tool_names=", ".join(self.tools.keys()),
                question=question,
                history=self._format_history()
            )

            response = self._call_llm(prompt)

            if "Final Answer:" in response:
                final_answer = response.split("Final Answer:")[1].strip()
                console.print(Panel(Markdown(final_answer), title="✅ Final Answer", border_style="green bold"))
                return final_answer

            # 简单的解析逻辑，假设响应包含 Thought 和 Action
            try:
                thought = response.split("Action:")[0].replace("Thought:", "").strip()
                action, action_input = self._parse_action(response)
            except Exception:
                thought = "Reasoning..."
                action, action_input = None, None

            observation = None
            if action and action_input:
                observation = self._execute_tool(action, action_input)

            step = AgentStep(thought=thought, action=action, action_input=action_input, observation=observation)
            self.history.append(step)
            self._display_step(step, iteration + 1)

        return "Max iterations reached."
    
    def reset(self):
        """Reset the agent's history"""
        self.history = []
        logger.info("Agent history reset")

if __name__ == "__main__":
    # 使用 Gemini 运行
    agent = CryptoReActAgent(llm_provider="gemini", model_name="gemini-2.5-flash")
    result = agent.run("What is the current price of Bitcoin and Ethereum?")