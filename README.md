# nodriver-mcp

Docker-based browser automation MCP using [nodriver](https://github.com/ultrafunkamsterdam/nodriver) - a browser automation library that can bypass bot detection.

## Features

- **Multi-instance support**: Each browser session runs in an isolated Docker container
- **Session management**: Create, destroy, and list browser sessions
- **Full browser automation**: Navigate, click, fill forms, take screenshots, etc.
- **Cookie/Storage management**: Get, set, and delete cookies and localStorage
- **Multi-tab support**: Open, switch between, and close tabs
- **Anti-detection**: Uses nodriver to avoid bot detection

## Installation

### 1. Build the browser container image

```bash
cd nodriver-mcp
docker build -t nodriver-mcp-browser .
```

### 2. Install the MCP server (using uv)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv with Python 3.11 and install
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

### 3. Configure Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nodriver": {
      "command": "/Users/user/Projects/chain-toolkit-group/nodriver-mcp/.venv/bin/python",
      "args": ["-m", "nodriver_mcp"]
    }
  }
}
```

## Usage

The MCP provides the following tools:

### Session Management

- `browser_create_session(headless=True)` - Create a new browser session
- `browser_destroy_session(session_id)` - Destroy a session
- `browser_list_sessions()` - List all active sessions

### Navigation

- `browser_navigate(session_id, url)` - Navigate to URL
- `browser_go_back(session_id)` - Go back
- `browser_go_forward(session_id)` - Go forward
- `browser_refresh(session_id)` - Refresh page

### Interaction

- `browser_click(session_id, selector)` - Click element
- `browser_fill(session_id, selector, value)` - Fill input field
- `browser_select(session_id, selector, value)` - Select dropdown option
- `browser_hover(session_id, selector)` - Hover over element
- `browser_scroll(session_id, x, y)` - Scroll page
- `browser_execute_js(session_id, script)` - Execute JavaScript

### Page Info

- `browser_get_content(session_id)` - Get HTML content
- `browser_get_text(session_id, selector?)` - Get text content
- `browser_screenshot(session_id, full_page?)` - Take screenshot
- `browser_get_url(session_id)` - Get current URL

### Wait

- `browser_wait_for_selector(session_id, selector, timeout?)` - Wait for element
- `browser_wait_for_navigation(session_id, timeout?)` - Wait for navigation

### Cookie/Storage

- `browser_get_cookies(session_id)` - Get cookies
- `browser_set_cookie(session_id, cookie)` - Set cookie
- `browser_delete_cookies(session_id, names?)` - Delete cookies
- `browser_get_local_storage(session_id)` - Get localStorage
- `browser_set_local_storage(session_id, key, value)` - Set localStorage item

### Tabs

- `browser_new_tab(session_id, url?)` - Open new tab
- `browser_switch_tab(session_id, tab_id)` - Switch to tab
- `browser_close_tab(session_id, tab_id)` - Close tab
- `browser_list_tabs(session_id)` - List all tabs

### Network

- `browser_intercept_requests(session_id, patterns, action)` - Set up interception
- `browser_get_network_logs(session_id)` - Get network logs

### Files

- `browser_upload_file(session_id, selector, file_path)` - Upload file
- `browser_download_file(session_id, url)` - Download file

## Example

```
User: Please log into example.com for me

Claude: I'll create a browser session and log in.

1. browser_create_session() → "abc123"
2. browser_navigate("abc123", "https://example.com/login")
3. browser_fill("abc123", "#username", "user")
4. browser_fill("abc123", "#password", "pass")
5. browser_click("abc123", "button[type=submit]")
6. browser_wait_for_navigation("abc123")
7. browser_screenshot("abc123") → [screenshot to verify]

Login successful! Here's a screenshot of the result.

8. browser_destroy_session("abc123")
```

## Architecture

```
┌─────────────────────────────────────────┐
│           Claude / AI Agent             │
└──────────────────┬──────────────────────┘
                   │ stdio (MCP Protocol)
┌──────────────────▼──────────────────────┐
│         nodriver-mcp (Host)             │
│  - Session management                   │
│  - Docker lifecycle management          │
│  - Request routing                      │
└────┬─────────────┬─────────────┬────────┘
     │ :9001       │ :9002       │ :9003
┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│Container│   │Container│   │Container│
│nodriver │   │nodriver │   │nodriver │
│+ Chrome │   │+ Chrome │   │+ Chrome │
└─────────┘   └─────────┘   └─────────┘
```

## Configuration

Environment variables for the MCP server:
- None required

Container environment variables:
- `HEADLESS` - Run browser in headless mode (default: `true`)
- `PORT` - Internal port for the FastAPI server (default: `9000`)

## Auto-cleanup

- Sessions automatically expire after 30 minutes of inactivity
- All containers are cleaned up when the MCP server stops
