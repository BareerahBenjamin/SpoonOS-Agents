# 🤝 贡献指南

感谢你考虑为 SpoonOS Agent Showcase 做出贡献！

## 📋 贡献方式

你可以通过以下方式贡献：

1. **报告 Bug** - 提交 Issue 描述问题
2. **建议功能** - 提出新功能想法
3. **改进文档** - 修正或完善文档
4. **提交代码** - 修复 Bug 或实现新功能
5. **分享使用案例** - 展示你的应用

## 🚀 快速开始

### 1. Fork 项目

点击 GitHub 页面右上角的 "Fork" 按钮。

### 2. 克隆你的 Fork

```bash
git clone https://github.com/your-username/spoon-agent-showcase.git
cd spoon-agent-showcase
```

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

分支命名规范：
- `feature/` - 新功能
- `fix/` - Bug 修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关

### 4. 设置开发环境

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

### 5. 进行修改

遵循我们的代码规范（见下文）。

### 6. 运行测试

```bash
pytest tests/ -v
```

### 7. 提交更改

```bash
git add .
git commit -m "feat: add amazing feature"
```

提交信息规范（Conventional Commits）：
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `style:` - 代码格式（不影响功能）
- `refactor:` - 重构
- `test:` - 测试
- `chore:` - 构建/工具

### 8. 推送到 GitHub

```bash
git push origin feature/your-feature-name
```

### 9. 创建 Pull Request

在 GitHub 上创建 Pull Request，描述你的更改。

## 📝 代码规范

### Python 代码风格

我们遵循 PEP 8 和以下规范：

```python
# 1. 导入顺序
import os  # 标准库
import sys

from typing import Dict, List  # 第三方库
import requests

from agents.react_agent import CryptoReActAgent  # 本地模块

# 2. 命名规范
class MyAgent:  # 类名：UpperCamelCase
    def my_method(self):  # 方法名：snake_case
        my_variable = 10  # 变量名：snake_case
        MY_CONSTANT = "value"  # 常量：UPPER_SNAKE_CASE

# 3. 文档字符串
def function_name(param: str) -> dict:
    """
    简短描述

    Args:
        param: 参数描述

    Returns:
        返回值描述
    """
    pass

# 4. 类型提示
def process_data(data: List[Dict[str, Any]]) -> Optional[str]:
    pass
```

### 代码检查

使用以下工具检查代码：

```bash
# 格式化
black agents/ tools/ examples/

# Lint 检查
ruff check agents/ tools/ examples/

# 类型检查
mypy agents/ tools/
```

### 测试规范

```python
# tests/test_my_feature.py

import pytest
from my_module import MyClass


class TestMyClass:
    """测试 MyClass"""

    def test_basic_functionality(self):
        """测试基本功能"""
        obj = MyClass()
        result = obj.method()
        assert result == expected_value

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试代码
        pass

    def test_error_handling(self):
        """测试错误处理"""
        with pytest.raises(ValueError):
            # 应该抛出错误的代码
            pass
```

## 🎯 贡献领域

### 优先级高的贡献

1. **添加新工具**
   - 更多数据源集成
   - Web3 工具
   - 分析工具

2. **改进 Agent**
   - 优化推理逻辑
   - 添加记忆功能
   - 多 Agent 协作

3. **完善文档**
   - 教程和示例
   - API 文档
   - 最佳实践

4. **性能优化**
   - 提示词缓存
   - 并行执行
   - 结果缓存

### 新功能建议

提交新功能前，请：

1. 在 Issues 中讨论想法
2. 确保功能有实际用途
3. 考虑向后兼容性
4. 编写测试和文档

## 🐛 报告 Bug

好的 Bug 报告应包含：

1. **清晰的标题** - 简短描述问题
2. **环境信息** - Python 版本、依赖版本
3. **重现步骤** - 详细步骤
4. **期望行为** - 应该发生什么
5. **实际行为** - 实际发生了什么
6. **错误信息** - 完整的错误堆栈
7. **截图** - 如果有帮助

模板：

```markdown
## 问题描述
简短描述问题

## 环境
- Python: 3.12
- SpoonOS: 0.1.0
- OS: macOS 14.0

## 重现步骤
1. 运行命令 X
2. 输入 Y
3. 观察错误

## 期望行为
应该输出 Z

## 实际行为
输出了错误 W

## 错误信息
```
粘贴完整错误堆栈
```

## 额外信息
其他相关信息
```

## 💡 功能请求

好的功能请求应包含：

1. **问题描述** - 要解决什么问题
2. **建议方案** - 你的想法
3. **替代方案** - 其他可能的方法
4. **使用场景** - 实际应用例子
5. **实现考虑** - 技术难点

## 📚 文档贡献

文档同样重要！你可以：

1. **修正错误** - 拼写、语法、技术错误
2. **改进清晰度** - 让说明更易懂
3. **添加示例** - 更多使用案例
4. **翻译** - 其他语言版本

文档格式：
- 使用 Markdown
- 代码块标注语言
- 添加清晰的标题层级
- 包含实际示例

## 🔍 代码审查

我们会审查所有 PR，可能会：

1. 提出修改建议
2. 要求添加测试
3. 要求改进文档
4. 讨论实现方式

请耐心等待和积极响应反馈！

## 🎁 贡献者福利

- 在 README 中列出所有贡献者
- 优秀贡献会在社交媒体宣传
- 有机会成为项目维护者

## ⚖️ 行为准则

我们承诺：

- 🤝 友善和尊重
- 💡 开放和包容
- 🎯 专注于项目目标
- ❤️ 支持新贡献者

不接受：

- ❌ 骚扰或歧视
- ❌ 攻击性语言
- ❌ 恶意行为

## 📞 联系方式

有问题？联系我们：

- GitHub Issues: [提交问题](https://github.com/your-username/spoon-agent-showcase/issues)
- Discord: [加入社区](https://discord.gg/xspoonai)
- Email: your-email@example.com

## 🙏 致谢

感谢所有贡献者让这个项目变得更好！

---

再次感谢你的贡献！每一个贡献都让项目更强大。💪✨
