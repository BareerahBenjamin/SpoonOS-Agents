# 本地运行与部署

工作台由一个 FastAPI 进程提供 React 静态页面、API 和 SSE，研究报告与运行事件写入 SQLite。

## Docker Compose

```bash
docker compose up --build -d
docker compose ps
```

打开 [研究工作台](http://127.0.0.1:8000/)。构建使用 `frontend/package-lock.json` 和 `uv.lock`，运行容器以非 root 用户启动。Compose 将服务端口绑定到本机回环地址。若 8000 已被占用，运行 `SPOONOS_PORT=8080 docker compose up --build -d`，然后访问 [127.0.0.1:8080](http://127.0.0.1:8080/)。

未提供 `.env` 时，容器使用无需密钥的演示模式。真实研究使用 `.env` 中的配置。修改配置后运行 `docker compose up -d`，Compose 会重新创建配置变化的容器。

报告与运行事件保存在 `research-data` 命名卷的 `/data/research.sqlite3`。`docker compose down` 会保留该卷。备份前停止服务，复制数据库后再启动。

```bash
docker compose stop workbench
docker compose cp workbench:/data/research.sqlite3 ./research-backup.sqlite3
docker compose start workbench
```

## 从源码运行

```bash
uv sync --locked --extra api
npm --prefix frontend ci
npm --prefix frontend run build
DEMO_MODE=true uv run --locked --extra api uvicorn service.app:create_app --factory --host 127.0.0.1 --port 8000
```

FastAPI 在启动时检测 `frontend/dist`。如果先启动了后端，完成首次前端构建后重启后端。`/docs` 提供接口文档，`/health` 检查进程存活并返回 SDK 版本。运行 `npm --prefix frontend run dev` 可在 Vite 中开发，API 和 SSE 会转发到后端的 8000 端口。

## 配置真实数据与模型

将 `.env.example` 复制为 `.env`，设置 `DEFAULT_LLM_PROVIDER` 和对应供应商的 API 密钥，保持 `DEMO_MODE=false`。从源码运行时去掉启动命令前的 `DEMO_MODE=true`。设置 `TAVILY_API_KEY` 可启用新闻和搜索。`COINGECKO_PLAN=demo` 对应可无密钥访问的公共 API。使用 Pro API 时需设置 `COINGECKO_PLAN=pro` 和 `COINGECKO_API_KEY`。

`.env` 在容器运行时注入，构建镜像时不会复制该文件。API 设置页只显示密钥的配置状态。网络代理可用标准的 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。

## 接口行为

`POST /research` 等待 LangGraph 运行，并在报告落库后返回 HTTP 201。正文的 `status` 表示数据和报告是否可用。新闻、历史和行情并行采集，模型由 SpoonOS 异步调用。

模型生成/输出校验失败返回已保存的 `failed` 研究结果；关键行情缺失返回 `unavailable`。无模型配置或非法配置返回 503，参数非法返回 422，报告不存在返回 404，无法解释未生成报告的任务返回 409，追问生成或引用验证失败返回 502。

`LLM_TIMEOUT_SECONDS` 限制一次模型生成或快速问答的总等待时间。行情/新闻每次 HTTP 请求有连接与读取超时，暂时性错误最多重试一次。通知默认关闭，启用时只发控制台。不会在 API 请求中触发 Slack/Discord/邮件投递。

## 保存与追问

源码运行时，`RESEARCH_DB_PATH` 默认为 `outputs/research.sqlite3`。每条记录包含完整报告、快照 ID、数据来源与时间、引用和节点事件。已保存的快照只读，数据库应按私有数据保存。

`GET /research` 查看历史，`GET /research/{run_id}` 取回同一份数据；`POST /research/{run_id}/questions` 只把已保存快照提供给模型。要使用最新行情，创建新的研究任务。

## 后台运行与 SSE

`POST /research/runs` 返回 `202` 和任务 ID。后台每次执行一项完整研究，最多再排队八项；队列满时返回 `429`。工作台从 `GET /research/runs/{run_id}/events` 订阅运行状态（`run`）、节点开始或结束（`node`），以及最终状态（`terminal`）。这些事件来自实际节点执行，报告中原有的 `events` 字段仍保留已结束节点的汇总。

SSE 用每个任务单独的递增整数 `id` 排序。客户端重连时传 `Last-Event-ID`，或首次连接时用 `?after=<id>`，服务只返回更大的事件 ID。空闲连接每 15 秒收到注释心跳；报告与终态在同一事务写入，收到成功终态即可读取报告。启用反向代理时，为 SSE 路由关闭响应缓冲和压缩，并让读取超时大于心跳间隔。

请让同一数据库只由一个应用进程执行任务（保持 Uvicorn 默认的 `--workers 1`）。断开页面不会取消后台研究。任务状态和已发事件存入 SQLite；应用重启会把尚未结束的运行标记为 `interrupted`，不会自动重试可能已收费的模型请求。

## 验证

```bash
uv run --locked --extra api --extra dev pytest -q
uv run --locked --extra api --extra dev ruff check agents tools service tests examples
npm --prefix frontend run build
docker compose config --quiet
```

默认测试不读取真实密钥或请求真实模型。外部服务的可用性与供应商账户的模型权限，需要配置真实密钥后实际运行确认。`DEMO_MODE=true` 可无模型密钥演示 Graph 数据状态，但不会生成投资结论。

## 多人或公网部署前的必要扩展

当前没有用户鉴权与任务归属隔离，请仅监听本机回环地址。多人版本需增加认证、任务归属检查、请求与费用限额，以及支持多进程的任务队列和数据库。
