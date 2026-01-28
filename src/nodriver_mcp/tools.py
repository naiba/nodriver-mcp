"""MCP tool definitions for browser automation."""

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .session_manager import get_session_manager


def register_tools(server: Server):
    """Register all browser automation tools with the MCP server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            # Session management
            Tool(
                name="browser_create_session",
                description="Create a new browser session in a Docker container. Returns a session_id to use for subsequent operations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "headless": {
                            "type": "boolean",
                            "description": "Run browser in headless mode (default: true)",
                            "default": True,
                        },
                        "proxy": {
                            "type": "string",
                            "description": "Optional proxy server URL (e.g., 'http://proxy:8080' or 'socks5://proxy:1080')",
                        },
                    },
                },
            ),
            Tool(
                name="browser_destroy_session",
                description="Destroy a browser session and its container.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session ID to destroy",
                        }
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_list_sessions",
                description="List all active browser sessions.",
                inputSchema={"type": "object", "properties": {}},
            ),
            # Navigation
            Tool(
                name="browser_navigate",
                description="Navigate to a URL in the browser.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "wait_until": {
                            "type": "string",
                            "description": "Wait until page load event (default: load)",
                            "default": "load",
                        },
                    },
                    "required": ["session_id", "url"],
                },
            ),
            Tool(
                name="browser_go_back",
                description="Go back in browser history.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_go_forward",
                description="Go forward in browser history.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_refresh",
                description="Refresh the current page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            # Interaction
            Tool(
                name="browser_click",
                description="Click on an element using a CSS selector.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {"type": "string", "description": "CSS selector of element to click"},
                    },
                    "required": ["session_id", "selector"],
                },
            ),
            Tool(
                name="browser_fill",
                description="Fill an input field with text.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {"type": "string", "description": "CSS selector of input element"},
                        "value": {"type": "string", "description": "Value to fill"},
                    },
                    "required": ["session_id", "selector", "value"],
                },
            ),
            Tool(
                name="browser_select",
                description="Select an option from a dropdown.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {"type": "string", "description": "CSS selector of select element"},
                        "value": {"type": "string", "description": "Value to select"},
                    },
                    "required": ["session_id", "selector", "value"],
                },
            ),
            Tool(
                name="browser_hover",
                description="Hover over an element.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {"type": "string", "description": "CSS selector of element"},
                    },
                    "required": ["session_id", "selector"],
                },
            ),
            Tool(
                name="browser_scroll",
                description="Scroll the page to a position.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "x": {"type": "integer", "description": "Horizontal scroll position"},
                        "y": {"type": "integer", "description": "Vertical scroll position"},
                    },
                    "required": ["session_id", "x", "y"],
                },
            ),
            Tool(
                name="browser_execute_js",
                description="Execute JavaScript code in the browser.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "script": {"type": "string", "description": "JavaScript code to execute"},
                    },
                    "required": ["session_id", "script"],
                },
            ),
            # Page info
            Tool(
                name="browser_get_content",
                description="Get the HTML content of the current page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_get_text",
                description="Get text content from the page or a specific element.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {
                            "type": "string",
                            "description": "CSS selector (optional, defaults to body)",
                        },
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_screenshot",
                description="Take a screenshot of the page. Returns base64 encoded image.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full page (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_get_url",
                description="Get the current URL of the page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            # Wait
            Tool(
                name="browser_wait_for_selector",
                description="Wait for an element to appear on the page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {"type": "string", "description": "CSS selector to wait for"},
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["session_id", "selector"],
                },
            ),
            Tool(
                name="browser_wait_for_navigation",
                description="Wait for page navigation to complete.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["session_id"],
                },
            ),
            # Cookies/Storage
            Tool(
                name="browser_get_cookies",
                description="Get all cookies from the current page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_set_cookie",
                description="Set a cookie.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "cookie": {
                            "type": "object",
                            "description": "Cookie object with name, value, and optional path, domain, expires",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "path": {"type": "string"},
                                "domain": {"type": "string"},
                                "expires": {"type": "string"},
                            },
                            "required": ["name", "value"],
                        },
                    },
                    "required": ["session_id", "cookie"],
                },
            ),
            Tool(
                name="browser_delete_cookies",
                description="Delete cookies.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Cookie names to delete (optional, deletes all if not specified)",
                        },
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_get_local_storage",
                description="Get all localStorage items.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_set_local_storage",
                description="Set a localStorage item.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "key": {"type": "string", "description": "Storage key"},
                        "value": {"type": "string", "description": "Storage value"},
                    },
                    "required": ["session_id", "key", "value"],
                },
            ),
            # Tabs
            Tool(
                name="browser_new_tab",
                description="Open a new browser tab.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "url": {"type": "string", "description": "URL to open (optional)"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_switch_tab",
                description="Switch to a different tab.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "tab_id": {"type": "string", "description": "Tab ID to switch to"},
                    },
                    "required": ["session_id", "tab_id"],
                },
            ),
            Tool(
                name="browser_close_tab",
                description="Close a browser tab.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "tab_id": {"type": "string", "description": "Tab ID to close"},
                    },
                    "required": ["session_id", "tab_id"],
                },
            ),
            Tool(
                name="browser_list_tabs",
                description="List all tabs in a session.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            # Network
            Tool(
                name="browser_intercept_requests",
                description="Set up network request interception (limited support).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URL patterns to intercept",
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to take (block, modify)",
                        },
                    },
                    "required": ["session_id", "patterns", "action"],
                },
            ),
            Tool(
                name="browser_get_network_logs",
                description="Get network request logs.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            # Files
            Tool(
                name="browser_upload_file",
                description="Upload a file to a file input element.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "selector": {"type": "string", "description": "CSS selector of file input"},
                        "file_path": {"type": "string", "description": "Local path to file"},
                    },
                    "required": ["session_id", "selector", "file_path"],
                },
            ),
            Tool(
                name="browser_download_file",
                description="Download a file from a URL.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "url": {"type": "string", "description": "URL to download from"},
                    },
                    "required": ["session_id", "url"],
                },
            ),
            # Performance
            Tool(
                name="browser_get_performance_metrics",
                description="Get performance metrics from CDP Performance.getMetrics(). Returns metrics like JSHeapUsedSize, LayoutCount, RecalcStyleCount, etc.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="browser_get_performance_timing",
                description="Get performance timing data including FCP, LCP, DOM load times, and other Web Vitals metrics.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                    },
                    "required": ["session_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        manager = get_session_manager()
        result: Any = None

        try:
            # Session management
            if name == "browser_create_session":
                headless = arguments.get("headless", True)
                proxy = arguments.get("proxy")
                session_id = await manager.create_session(headless=headless, proxy=proxy)
                result = {"session_id": session_id}

            elif name == "browser_destroy_session":
                success = await manager.destroy_session(arguments["session_id"])
                result = {"success": success}

            elif name == "browser_list_sessions":
                result = manager.list_sessions()

            # Navigation
            elif name == "browser_navigate":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/navigate",
                    json={"url": arguments["url"], "wait_until": arguments.get("wait_until", "load")},
                )

            elif name == "browser_go_back":
                result = await manager.request(arguments["session_id"], "POST", "/go_back")

            elif name == "browser_go_forward":
                result = await manager.request(arguments["session_id"], "POST", "/go_forward")

            elif name == "browser_refresh":
                result = await manager.request(arguments["session_id"], "POST", "/refresh")

            # Interaction
            elif name == "browser_click":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/click",
                    json={"selector": arguments["selector"]},
                )

            elif name == "browser_fill":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/fill",
                    json={"selector": arguments["selector"], "value": arguments["value"]},
                )

            elif name == "browser_select":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/select",
                    json={"selector": arguments["selector"], "value": arguments["value"]},
                )

            elif name == "browser_hover":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/hover",
                    json={"selector": arguments["selector"]},
                )

            elif name == "browser_scroll":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/scroll",
                    json={"x": arguments["x"], "y": arguments["y"]},
                )

            elif name == "browser_execute_js":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/execute_js",
                    json={"script": arguments["script"]},
                )

            # Page info
            elif name == "browser_get_content":
                result = await manager.request(arguments["session_id"], "GET", "/get_content")

            elif name == "browser_get_text":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/get_text",
                    json={"selector": arguments.get("selector")},
                )

            elif name == "browser_screenshot":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/screenshot",
                    json={"full_page": arguments.get("full_page", False)},
                )

            elif name == "browser_get_url":
                result = await manager.request(arguments["session_id"], "GET", "/get_url")

            # Wait
            elif name == "browser_wait_for_selector":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/wait_for_selector",
                    json={"selector": arguments["selector"], "timeout": arguments.get("timeout", 30)},
                )

            elif name == "browser_wait_for_navigation":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/wait_for_navigation",
                    json={"timeout": arguments.get("timeout", 30)},
                )

            # Cookies/Storage
            elif name == "browser_get_cookies":
                result = await manager.request(arguments["session_id"], "GET", "/get_cookies")

            elif name == "browser_set_cookie":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/set_cookie",
                    json={"cookie": arguments["cookie"]},
                )

            elif name == "browser_delete_cookies":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/delete_cookies",
                    json={"names": arguments.get("names")},
                )

            elif name == "browser_get_local_storage":
                result = await manager.request(arguments["session_id"], "GET", "/get_local_storage")

            elif name == "browser_set_local_storage":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/set_local_storage",
                    json={"key": arguments["key"], "value": arguments["value"]},
                )

            # Tabs
            elif name == "browser_new_tab":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/new_tab",
                    json={"url": arguments.get("url")},
                )

            elif name == "browser_switch_tab":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/switch_tab",
                    json={"tab_id": arguments["tab_id"]},
                )

            elif name == "browser_close_tab":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/close_tab",
                    json={"tab_id": arguments["tab_id"]},
                )

            elif name == "browser_list_tabs":
                result = await manager.request(arguments["session_id"], "GET", "/list_tabs")

            # Network
            elif name == "browser_intercept_requests":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/intercept_requests",
                    json={"patterns": arguments["patterns"], "action": arguments["action"]},
                )

            elif name == "browser_get_network_logs":
                result = await manager.request(arguments["session_id"], "GET", "/get_network_logs")

            # Files
            elif name == "browser_upload_file":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/upload_file",
                    json={"selector": arguments["selector"], "file_path": arguments["file_path"]},
                )

            elif name == "browser_download_file":
                result = await manager.request(
                    arguments["session_id"],
                    "POST",
                    "/download_file",
                    json={"url": arguments["url"]},
                )

            # Performance
            elif name == "browser_get_performance_metrics":
                result = await manager.request(arguments["session_id"], "GET", "/get_performance_metrics")

            elif name == "browser_get_performance_timing":
                result = await manager.request(arguments["session_id"], "GET", "/get_performance_timing")

            else:
                result = {"error": f"Unknown tool: {name}"}

        except Exception as e:
            result = {"error": str(e)}

        import json
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
