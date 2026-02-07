# 🥄 SpoonOS Agent Showcase

一个使用 SpoonOS 框架实现的智能加密货币分析助手，展示 ReAct Agent 和 Graph Agent 的强大能力。

## 🌟 项目特点

- **ReAct Agent**: 基于推理-行动模式的智能问答系统
- **Graph Agent**: 状态图驱动的复杂工作流编排
- **多模型支持**: OpenAI、Anthropic、DeepSeek 等
- **Web3 集成**: 区块链数据查询和交互
- **工具生态**: 集成搜索、数据分析、通知等多种工具

## 🏗️ 项目架构

```
spoon-agent-showcase/
├── agents/
│   ├── react_agent.py      # ReAct Agent 实现
│   └── graph_agent.py      # Graph Agent 实现
├── tools/
│   ├── crypto_tools.py     # 加密货币工具
│   ├── search_tools.py     # 搜索工具
│   └── notification_tools.py # 通知工具
├── skills/
│   └── crypto_analysis/    # 自定义 Skill
├── examples/
│   ├── react_demo.py       # ReAct Agent 演示
│   └── graph_demo.py       # Graph Agent 演示
├── tests/
│   ├── test_react_agent.py
│   └── test_graph_agent.py
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🚀 快速开始

### 1. 环境准备

**系统要求**:
- Python 3.12+
- pip 或 uv 包管理器

**克隆项目**:
```bash
git clone https://github.com/your-username/spoon-agent-showcase.git
cd spoon-agent-showcase
```

### 2. 安装依赖

使用 pip:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

或使用 uv (更快):
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，添加你的 API 密钥：
```bash
# LLM Provider
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
DEEPSEEK_API_KEY=your_deepseek_key

# Tools
TAVILY_API_KEY=your_tavily_key
COINGECKO_API_KEY=your_coingecko_key

# Optional: Web3
WEB3_RPC_URL=your_rpc_url
```

### 4. 运行演示

**ReAct Agent 演示**:
```bash
python examples/react_demo.py
```

**Graph Agent 演示**:
```bash
python examples/graph_demo.py
```

## 📚 使用示例

### ReAct Agent - 智能问答

```python
from agents.react_agent import CryptoReActAgent

# 初始化 Agent
agent = CryptoReActAgent(
    llm_provider="openai",
    model_name="gpt-4"
)

# 提问
response = agent.run(
    "比特币当前价格是多少？最近24小时涨跌幅如何？"
)

print(response)
```

**工作流程**:
1. **Thought**: Agent 分析问题，决定需要查询价格数据
2. **Action**: 调用 `get_crypto_price` 工具
3. **Observation**: 获取价格数据
4. **Thought**: 分析数据，准备回答
5. **Answer**: 生成最终答案

### Graph Agent - 工作流编排

```python
from agents.graph_agent import CryptoAnalysisGraph

# 初始化 Graph Agent
graph = CryptoAnalysisGraph()

# 运行工作流
result = graph.run({
    "symbol": "BTC",
    "action": "analyze"
})

print(result)
```

**工作流节点**:
1. **数据收集**: 获取价格、交易量、市值
2. **技术分析**: 计算指标（RSI、MACD、MA）
3. **情绪分析**: 分析社交媒体和新闻
4. **决策生成**: 综合分析生成建议
5. **通知发送**: 发送分析报告

## 🛠️ 核心组件

### 1. ReAct Agent

ReAct（Reasoning + Acting）模式结合了推理和行动：

```python
class ReActAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def run(self, query):
        while not self.is_finished():
            # Reasoning
            thought = self.llm.generate_thought(query, self.history)

            # Acting
            if self.should_use_tool(thought):
                action = self.select_action(thought)
                observation = self.execute_tool(action)
                self.history.append({
                    "thought": thought,
                    "action": action,
                    "observation": observation
                })
            else:
                return self.generate_answer(thought)
```

### 2. Graph Agent

基于状态图的工作流编排：

```python
from langgraph.graph import StateGraph

class GraphAgent:
    def __init__(self):
        self.graph = StateGraph()

    def build_graph(self):
        # 添加节点
        self.graph.add_node("collect", self.collect_data)
        self.graph.add_node("analyze", self.analyze_data)
        self.graph.add_node("decide", self.make_decision)

        # 添加边
        self.graph.add_edge("collect", "analyze")
        self.graph.add_edge("analyze", "decide")

        # 设置入口和出口
        self.graph.set_entry_point("collect")
        self.graph.set_finish_point("decide")

        return self.graph.compile()
```

## 🔧 自定义工具

创建自定义工具非常简单：

```python
from spoon_toolkit.base import BaseTool

class CustomCryptoTool(BaseTool):
    name = "custom_crypto_tool"
    description = "获取加密货币的自定义数据"

    def _run(self, symbol: str) -> dict:
        # 实现你的逻辑
        return {
            "symbol": symbol,
            "data": "..."
        }
```

## 🧪 测试

运行所有测试：
```bash
pytest tests/
```

运行特定测试：
```bash
pytest tests/test_react_agent.py -v
```

## 📊 性能优化

- **提示词缓存**: 使用 Anthropic 的 prompt caching 减少成本
- **流式响应**: 实时显示 LLM 生成内容
- **工具并行**: 支持多个工具同时执行
- **状态持久化**: Graph Agent 支持状态保存和恢复

## 🌐 Web3 集成

项目包含完整的 Web3 功能：

```python
from tools.web3_tools import Web3Tools

web3 = Web3Tools()

# 查询余额
balance = web3.get_balance("0x...")

# 执行交易
tx = web3.send_transaction({
    "to": "0x...",
    "value": 1000000000000000000  # 1 ETH
})
```

## 📹 演示视频

[点击观看完整演示视频](https://www.bilibili.com/video/BV14HFxzPEs7/)

视频内容：
1. 项目介绍和架构说明
2. ReAct Agent 实时演示
3. Graph Agent 工作流展示
4. 工具和 Skill 集成演示
5. 代码结构讲解

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

Apache 2.0 License - 查看 [LICENSE](LICENSE) 文件

## 🔗 相关资源

- [SpoonOS 官方文档](https://xspoonai.github.io/)
- [SpoonOS Core](https://github.com/XSpoonAi/spoon-core)
- [SpoonOS Toolkit](https://github.com/XSpoonAi/spoon-toolkit)
- [Awesome Skills](https://github.com/XSpoonAi/spoon-awesome-skill)

## 📧 联系方式

- GitHub Issues: [提交问题](https://github.com/your-username/spoon-agent-showcase/issues)
- Discord: [加入社区](https://discord.gg/xspoonai)

## 🙏 致谢

感谢 SpoonOS 团队提供的强大框架和工具！

---

⭐ 如果这个项目对你有帮助，请给一个 Star！
