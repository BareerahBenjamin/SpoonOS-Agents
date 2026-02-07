# 🚀 部署指南

本指南介绍如何将 SpoonOS Agent Showcase 部署到各种环境。

## 📋 目录

- [本地开发环境](#本地开发环境)
- [Docker 部署](#docker-部署)
- [云平台部署](#云平台部署)
- [API 服务化](#api-服务化)
- [监控和日志](#监控和日志)

## 本地开发环境

### 系统要求

- Python 3.12+
- 4GB+ RAM
- 网络连接（访问 LLM API）

### 快速部署

```bash
# 1. 克隆项目
git clone https://github.com/your-username/spoon-agent-showcase.git
cd spoon-agent-showcase

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加 API Keys

# 5. 运行演示
python examples/react_demo.py
```

## Docker 部署

### Dockerfile

创建 `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 暴露端口（如果运行 API 服务）
EXPOSE 8000

# 默认命令
CMD ["python", "examples/react_demo.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  spoon-agent:
    build: .
    container_name: spoon-agent-showcase
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DEFAULT_LLM_PROVIDER=${DEFAULT_LLM_PROVIDER}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### 构建和运行

```bash
# 构建镜像
docker build -t spoon-agent-showcase .

# 运行容器
docker run -it --env-file .env spoon-agent-showcase

# 使用 docker-compose
docker-compose up -d
```

## 云平台部署

### AWS Lambda

#### 1. 准备部署包

```bash
# 安装依赖到目录
pip install -r requirements.txt -t ./package

# 打包代码
cd package
zip -r ../deployment.zip .
cd ..
zip -g deployment.zip agents/ tools/ examples/
```

#### 2. 创建 Lambda 函数

使用 AWS CLI:

```bash
aws lambda create-function \
  --function-name spoon-agent-showcase \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler lambda_handler.handler \
  --zip-file fileb://deployment.zip \
  --timeout 300 \
  --memory-size 1024
```

#### 3. Lambda Handler

创建 `lambda_handler.py`:

```python
import json
from agents.react_agent import CryptoReActAgent


def handler(event, context):
    """Lambda handler for ReAct Agent"""

    # 解析请求
    body = json.loads(event.get('body', '{}'))
    question = body.get('question', '')

    # 初始化 Agent
    agent = CryptoReActAgent(
        llm_provider="openai",
        model_name="gpt-4-turbo-preview",
        verbose=False
    )

    # 运行 Agent
    result = agent.run(question)

    # 返回响应
    return {
        'statusCode': 200,
        'body': json.dumps({
            'answer': result,
            'question': question
        })
    }
```

### Google Cloud Run

#### 1. 创建 Dockerfile

使用上面的 Dockerfile。

#### 2. 构建并推送镜像

```bash
# 构建镜像
gcloud builds submit --tag gcr.io/YOUR_PROJECT/spoon-agent-showcase

# 部署到 Cloud Run
gcloud run deploy spoon-agent-showcase \
  --image gcr.io/YOUR_PROJECT/spoon-agent-showcase \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your-key
```

### Heroku

#### 1. 创建 Procfile

```
web: python api_server.py
```

#### 2. 部署

```bash
# 登录 Heroku
heroku login

# 创建应用
heroku create spoon-agent-showcase

# 设置环境变量
heroku config:set OPENAI_API_KEY=your-key

# 推送代码
git push heroku main
```

### Railway

#### 1. 连接 GitHub 仓库

在 Railway 上连接你的 GitHub 仓库。

#### 2. 配置环境变量

在 Railway 仪表板中添加：
- `OPENAI_API_KEY`
- `DEFAULT_LLM_PROVIDER`
- `DEFAULT_MODEL_NAME`

#### 3. 自动部署

Railway 会自动检测 Python 项目并部署。

## API 服务化

### 创建 FastAPI 服务

创建 `api_server.py`:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.react_agent import CryptoReActAgent
from agents.graph_agent import CryptoAnalysisGraph

app = FastAPI(title="SpoonOS Agent API")


class QuestionRequest(BaseModel):
    question: str
    agent_type: str = "react"


class AnalysisRequest(BaseModel):
    symbol: str


@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    """Ask a question to the ReAct Agent"""
    try:
        agent = CryptoReActAgent(verbose=False)
        result = agent.run(request.question)
        return {"answer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_crypto(request: AnalysisRequest):
    """Analyze a cryptocurrency"""
    try:
        agent = CryptoAnalysisGraph(verbose=False)
        result = agent.run(symbol=request.symbol)
        return {
            "symbol": result.symbol,
            "recommendation": result.recommendation,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 运行 API 服务

```bash
# 安装 FastAPI 和 Uvicorn
pip install fastapi uvicorn

# 运行服务
python api_server.py

# 或使用 Uvicorn
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 提问
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the price of Bitcoin?"}'

# 分析
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC"}'
```

## 监控和日志

### 日志配置

使用 Loguru 配置日志：

```python
from loguru import logger

# 配置日志
logger.add(
    "logs/agent_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)
```

### 性能监控

#### 1. 使用 Prometheus

```python
from prometheus_client import Counter, Histogram, start_http_server

# 定义指标
requests_total = Counter('agent_requests_total', 'Total requests')
request_duration = Histogram('agent_request_duration_seconds', 'Request duration')

# 在代码中使用
requests_total.inc()
with request_duration.time():
    result = agent.run(question)
```

#### 2. 使用 Sentry

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

### 错误追踪

```python
import traceback

try:
    result = agent.run(question)
except Exception as e:
    logger.error(f"Error: {e}")
    logger.error(traceback.format_exc())
    # 发送告警
```

## 生产环境最佳实践

### 1. 安全性

- **API Keys**: 使用环境变量或密钥管理服务
- **HTTPS**: 强制使用 HTTPS
- **认证**: 添加 API 认证（JWT、API Key）
- **限流**: 实现请求限流

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/ask")
@limiter.limit("10/minute")
async def ask_question(request: Request):
    pass
```

### 2. 性能优化

- **缓存**: 缓存常见查询结果
- **异步**: 使用异步 I/O
- **连接池**: 复用 HTTP 连接
- **提示词缓存**: 使用 Anthropic 提示词缓存

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_crypto_price(symbol: str):
    # 缓存价格查询
    pass
```

### 3. 可靠性

- **重试机制**: 自动重试失败请求
- **超时控制**: 设置合理超时
- **熔断器**: 防止级联失败
- **健康检查**: 定期健康检查

```python
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10)
)
def call_llm_with_retry():
    pass
```

### 4. 可观测性

- **日志**: 结构化日志
- **指标**: 关键业务指标
- **追踪**: 分布式追踪
- **告警**: 异常告警

## 扩展部署

### 水平扩展

使用 Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spoon-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: spoon-agent
  template:
    metadata:
      labels:
        app: spoon-agent
    spec:
      containers:
      - name: spoon-agent
        image: spoon-agent-showcase:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
```

### 负载均衡

使用 Nginx:

```nginx
upstream spoon_agent {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://spoon_agent;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 环境变量清单

生产环境必需的环境变量：

```bash
# LLM Provider
OPENAI_API_KEY=required
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4-turbo-preview

# Tools
TAVILY_API_KEY=optional
COINGECKO_API_KEY=optional

# Application
LOG_LEVEL=INFO
MAX_ITERATIONS=10
ENABLE_STREAMING=false

# API (如果部署 API)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*

# Monitoring
SENTRY_DSN=optional
PROMETHEUS_PORT=9090
```

## 故障排除

### 常见问题

1. **内存不足**
   - 增加容器内存限制
   - 使用更小的模型
   - 实现结果缓存

2. **API 超时**
   - 增加超时时间
   - 使用更快的模型
   - 实现异步处理

3. **并发问题**
   - 使用异步框架
   - 增加工作进程数
   - 实现请求队列

## 总结

选择合适的部署方式：

- **开发**: 本地环境
- **原型**: Docker
- **小型应用**: Heroku/Railway
- **中型应用**: AWS Lambda/Cloud Run
- **大型应用**: Kubernetes

记住：
- ✅ 始终使用环境变量管理敏感信息
- ✅ 实现完善的日志和监控
- ✅ 定期备份数据
- ✅ 进行性能测试

祝部署顺利！🚀
