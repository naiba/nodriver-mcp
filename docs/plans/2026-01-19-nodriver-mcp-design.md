# Nodriver MCP 设计文档

## 概述

基于 Docker 的 nodriver MCP，为 AI Agent 提供浏览器自动化能力，支持多实例并发运行。

## 架构

```
┌────────────────────────────────────────────────────────────┐
│                      Claude / AI Agent                      │
└─────────────────────────────────────┬──────────────────────┘
                                      │ stdio (MCP Protocol)
┌─────────────────────────────────────▼──────────────────────┐
│              nodriver-mcp (宿主机 Python)                   │
│  - 会话管理: create/destroy/list sessions                   │
│  - Docker 容器生命周期管理                                   │
│  - 请求路由: session_id → container HTTP API                │
└────────┬─────────────────┬─────────────────┬───────────────┘
         │ :9001           │ :9002           │ :9003
┌────────▼───────┐  ┌──────▼────────┐  ┌────▼────────────┐
│   Container A  │  │  Container B  │  │   Container C   │
│ ┌────────────┐ │  │ ┌───────────┐ │  │ ┌────────────┐  │
│ │ HTTP Server│ │  │ │HTTP Server│ │  │ │ HTTP Server│  │
│ │ (FastAPI)  │ │  │ │ (FastAPI) │ │  │ │ (FastAPI)  │  │
│ └─────┬──────┘ │  │ └─────┬─────┘ │  │ └─────┬──────┘  │
│ ┌─────▼──────┐ │  │ ┌─────▼─────┐ │  │ ┌─────▼──────┐  │
│ │  nodriver  │ │  │ │ nodriver  │ │  │ │  nodriver  │  │
│ │  + Chrome  │ │  │ │ + Chrome  │ │  │ │  + Chrome  │  │
│ └────────────┘ │  │ └───────────┘ │  │ └────────────┘  │
└────────────────┘  └───────────────┘  └─────────────────┘
```

**关键设计决策：**
- MCP Server 在宿主机运行，通过 Docker API 管理容器
- 每个容器 = 一个浏览器会话 = 一个 session_id
- 容器内 FastAPI 提供 HTTP API，宿主机 MCP Server 转发请求
- 动态端口分配（9001 起始）

## MCP 工具定义

### 会话管理
- `create_session(headless: bool = True) → session_id`
- `destroy_session(session_id: str) → bool`
- `list_sessions() → [{id, status, created_at, current_url}]`

### 导航
- `navigate(session_id, url: str, wait_until: str = "load") → page_info`
- `go_back(session_id) → page_info`
- `go_forward(session_id) → page_info`
- `refresh(session_id) → page_info`

### 页面交互
- `click(session_id, selector: str) → bool`
- `fill(session_id, selector: str, value: str) → bool`
- `select(session_id, selector: str, value: str) → bool`
- `hover(session_id, selector: str) → bool`
- `scroll(session_id, x: int, y: int) → bool`
- `execute_js(session_id, script: str) → any`

### 页面信息
- `get_content(session_id) → html`
- `get_text(session_id, selector: str = None) → text`
- `screenshot(session_id, full_page: bool = False) → base64_image`
- `get_url(session_id) → url`

### 等待
- `wait_for_selector(session_id, selector: str, timeout: int = 30) → bool`
- `wait_for_navigation(session_id, timeout: int = 30) → bool`

### Cookie/Storage
- `get_cookies(session_id) → [cookies]`
- `set_cookie(session_id, cookie: dict) → bool`
- `delete_cookies(session_id, names: list = None) → bool`
- `get_local_storage(session_id) → dict`
- `set_local_storage(session_id, key: str, value: str) → bool`

### 多标签页
- `new_tab(session_id, url: str = None) → tab_id`
- `switch_tab(session_id, tab_id: str) → bool`
- `close_tab(session_id, tab_id: str) → bool`
- `list_tabs(session_id) → [tabs]`

### 网络
- `intercept_requests(session_id, patterns: list, action: str) → bool`
- `get_network_logs(session_id) → [requests]`

### 文件
- `upload_file(session_id, selector: str, file_path: str) → bool`
- `download_file(session_id, url: str) → local_path`

## Docker 容器设计

### Dockerfile
```dockerfile
FROM python:3.11-slim

# 安装 Chrome 依赖
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip install nodriver fastapi uvicorn

COPY server.py /app/
WORKDIR /app

EXPOSE 9000
CMD ["python", "server.py"]
```

### 容器特性
- 使用 `--shm-size=2g` 防止 Chrome 崩溃
- 可选挂载 `/tmp/downloads` 用于文件下载
- 健康检查端点 `/health`
- 无状态设计，销毁即清理

## 项目结构

```
nodriver-mcp/
├── pyproject.toml
├── Dockerfile              # 浏览器容器镜像
├── src/
│   └── nodriver_mcp/
│       ├── __init__.py
│       ├── server.py       # MCP Server 入口
│       ├── session_manager.py  # Docker 容器生命周期
│       ├── tools.py        # MCP 工具定义
│       └── container/
│           └── server.py   # 容器内 FastAPI 服务
└── README.md
```

## SessionManager 核心逻辑

```python
class SessionManager:
    def __init__(self):
        self.sessions: dict[str, SessionInfo] = {}
        self.port_counter = 9001
        self.docker_client = docker.from_env()

    async def create(self, headless=True) -> str:
        session_id = uuid4().hex[:8]
        port = self._allocate_port()
        container = self.docker_client.containers.run(
            "nodriver-mcp-browser",
            detach=True,
            ports={"9000/tcp": port},
            shm_size="2g",
            environment={"HEADLESS": str(headless)},
            name=f"nodriver-{session_id}"
        )
        self.sessions[session_id] = SessionInfo(
            container=container, port=port, created_at=now()
        )
        await self._wait_healthy(port)
        return session_id

    async def destroy(self, session_id: str):
        info = self.sessions.pop(session_id)
        info.container.stop()
        info.container.remove()
```

## 部署与使用

### 安装
```bash
cd nodriver-mcp
pip install -e .

# 构建浏览器容器镜像
docker build -t nodriver-mcp-browser .
```

### Claude Desktop 配置
```json
{
  "mcpServers": {
    "nodriver": {
      "command": "python",
      "args": ["-m", "nodriver_mcp"]
    }
  }
}
```

### 使用示例
```
AI: 我需要访问某网站并登录
   → create_session() → "abc123"
   → navigate("abc123", "https://example.com/login")
   → fill("abc123", "#username", "user")
   → fill("abc123", "#password", "pass")
   → click("abc123", "button[type=submit]")
   → wait_for_navigation("abc123")
   → screenshot("abc123") → 确认登录成功
   → ... 更多操作 ...
   → destroy_session("abc123")
```

### 自动清理
- MCP Server 退出时自动销毁所有容器
- 可配置会话超时时间（默认 30 分钟无操作自动销毁）
