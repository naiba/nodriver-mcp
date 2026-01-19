"""FastAPI server running inside Docker container for browser automation."""

import asyncio
import base64
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import nodriver as uc
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Global browser instance
browser: uc.Browser | None = None
tabs: dict[str, uc.Tab] = {}
current_tab_id: str | None = None
network_logs: list[dict] = []


class NavigateRequest(BaseModel):
    url: str
    wait_until: str = "load"


class ClickRequest(BaseModel):
    selector: str


class FillRequest(BaseModel):
    selector: str
    value: str


class SelectRequest(BaseModel):
    selector: str
    value: str


class HoverRequest(BaseModel):
    selector: str


class ScrollRequest(BaseModel):
    x: int
    y: int


class ExecuteJsRequest(BaseModel):
    script: str


class GetTextRequest(BaseModel):
    selector: str | None = None


class ScreenshotRequest(BaseModel):
    full_page: bool = False


class WaitForSelectorRequest(BaseModel):
    selector: str
    timeout: int = 30


class WaitForNavigationRequest(BaseModel):
    timeout: int = 30


class SetCookieRequest(BaseModel):
    cookie: dict


class DeleteCookiesRequest(BaseModel):
    names: list[str] | None = None


class SetLocalStorageRequest(BaseModel):
    key: str
    value: str


class NewTabRequest(BaseModel):
    url: str | None = None


class SwitchTabRequest(BaseModel):
    tab_id: str


class CloseTabRequest(BaseModel):
    tab_id: str


class InterceptRequest(BaseModel):
    patterns: list[str]
    action: str


class UploadFileRequest(BaseModel):
    selector: str
    file_path: str


class DownloadFileRequest(BaseModel):
    url: str


def get_current_tab() -> uc.Tab:
    """Get the current active tab."""
    global current_tab_id, tabs
    if current_tab_id is None or current_tab_id not in tabs:
        raise HTTPException(status_code=400, detail="No active tab")
    return tabs[current_tab_id]


def generate_tab_id() -> str:
    """Generate a unique tab ID."""
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage browser lifecycle."""
    global browser, tabs, current_tab_id

    headless = os.environ.get("HEADLESS", "true").lower() == "true"

    browser = await uc.start(
        headless=headless,
        browser_args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
        ]
    )

    # Create initial tab
    tab = await browser.get("about:blank")
    tab_id = generate_tab_id()
    tabs[tab_id] = tab
    current_tab_id = tab_id

    yield

    # Cleanup
    if browser:
        browser.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "browser": browser is not None}


@app.get("/status")
async def status():
    """Get current browser status."""
    tab = get_current_tab()
    return {
        "current_url": tab.url if tab else None,
        "tab_count": len(tabs),
        "current_tab_id": current_tab_id,
    }


# Navigation endpoints

@app.post("/navigate")
async def navigate(req: NavigateRequest):
    """Navigate to a URL."""
    tab = get_current_tab()
    await tab.get(req.url)
    return {"url": tab.url, "title": await tab.get_content() and tab.target.title}


@app.post("/go_back")
async def go_back():
    """Go back in history."""
    tab = get_current_tab()
    await tab.back()
    return {"url": tab.url}


@app.post("/go_forward")
async def go_forward():
    """Go forward in history."""
    tab = get_current_tab()
    await tab.forward()
    return {"url": tab.url}


@app.post("/refresh")
async def refresh():
    """Refresh the page."""
    tab = get_current_tab()
    await tab.reload()
    return {"url": tab.url}


# Interaction endpoints

@app.post("/click")
async def click(req: ClickRequest):
    """Click an element."""
    tab = get_current_tab()
    element = await tab.select(req.selector)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element not found: {req.selector}")
    await element.click()
    return {"success": True}


@app.post("/fill")
async def fill(req: FillRequest):
    """Fill an input field."""
    tab = get_current_tab()
    element = await tab.select(req.selector)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element not found: {req.selector}")
    await element.clear_input()
    await element.send_keys(req.value)
    return {"success": True}


@app.post("/select")
async def select_option(req: SelectRequest):
    """Select an option from a dropdown."""
    tab = get_current_tab()
    element = await tab.select(req.selector)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element not found: {req.selector}")
    await tab.evaluate(
        f"document.querySelector('{req.selector}').value = '{req.value}'"
    )
    return {"success": True}


@app.post("/hover")
async def hover(req: HoverRequest):
    """Hover over an element."""
    tab = get_current_tab()
    element = await tab.select(req.selector)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element not found: {req.selector}")
    await element.mouse_move()
    return {"success": True}


@app.post("/scroll")
async def scroll(req: ScrollRequest):
    """Scroll the page."""
    tab = get_current_tab()
    await tab.evaluate(f"window.scrollTo({req.x}, {req.y})")
    return {"success": True}


@app.post("/execute_js")
async def execute_js(req: ExecuteJsRequest):
    """Execute JavaScript."""
    tab = get_current_tab()
    result = await tab.evaluate(req.script)
    return {"result": result}


# Page info endpoints

@app.get("/get_content")
async def get_content():
    """Get page HTML content."""
    tab = get_current_tab()
    content = await tab.get_content()
    return {"content": content}


@app.post("/get_text")
async def get_text(req: GetTextRequest):
    """Get text content."""
    tab = get_current_tab()
    if req.selector:
        element = await tab.select(req.selector)
        if not element:
            raise HTTPException(status_code=404, detail=f"Element not found: {req.selector}")
        text = await tab.evaluate(f"document.querySelector('{req.selector}').innerText")
    else:
        text = await tab.evaluate("document.body.innerText")
    return {"text": text}


@app.post("/screenshot")
async def screenshot(req: ScreenshotRequest):
    """Take a screenshot."""
    tab = get_current_tab()
    screenshot_bytes = await tab.save_screenshot()
    if screenshot_bytes:
        with open(screenshot_bytes, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        os.remove(screenshot_bytes)
        return {"image": b64}
    raise HTTPException(status_code=500, detail="Failed to take screenshot")


@app.get("/get_url")
async def get_url():
    """Get current URL."""
    tab = get_current_tab()
    return {"url": tab.url}


# Wait endpoints

@app.post("/wait_for_selector")
async def wait_for_selector(req: WaitForSelectorRequest):
    """Wait for a selector to appear."""
    tab = get_current_tab()
    try:
        element = await tab.select(req.selector, timeout=req.timeout)
        return {"found": element is not None}
    except Exception:
        return {"found": False}


@app.post("/wait_for_navigation")
async def wait_for_navigation(req: WaitForNavigationRequest):
    """Wait for navigation to complete."""
    tab = get_current_tab()
    await asyncio.sleep(1)  # Basic wait, nodriver handles most waits automatically
    return {"url": tab.url}


# Cookie/Storage endpoints

@app.get("/get_cookies")
async def get_cookies():
    """Get all cookies."""
    tab = get_current_tab()
    cookies = await tab.evaluate("document.cookie")
    return {"cookies": cookies}


@app.post("/set_cookie")
async def set_cookie(req: SetCookieRequest):
    """Set a cookie."""
    tab = get_current_tab()
    cookie = req.cookie
    cookie_str = f"{cookie.get('name')}={cookie.get('value')}"
    if cookie.get("path"):
        cookie_str += f"; path={cookie['path']}"
    if cookie.get("domain"):
        cookie_str += f"; domain={cookie['domain']}"
    if cookie.get("expires"):
        cookie_str += f"; expires={cookie['expires']}"
    await tab.evaluate(f"document.cookie = '{cookie_str}'")
    return {"success": True}


@app.post("/delete_cookies")
async def delete_cookies(req: DeleteCookiesRequest):
    """Delete cookies."""
    tab = get_current_tab()
    if req.names:
        for name in req.names:
            await tab.evaluate(
                f"document.cookie = '{name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'"
            )
    else:
        # Delete all cookies
        cookies = await tab.evaluate("document.cookie")
        for cookie in cookies.split(";"):
            name = cookie.split("=")[0].strip()
            await tab.evaluate(
                f"document.cookie = '{name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'"
            )
    return {"success": True}


@app.get("/get_local_storage")
async def get_local_storage():
    """Get all localStorage items."""
    tab = get_current_tab()
    storage = await tab.evaluate(
        "JSON.stringify(Object.fromEntries(Object.entries(localStorage)))"
    )
    return {"storage": json.loads(storage) if storage else {}}


@app.post("/set_local_storage")
async def set_local_storage(req: SetLocalStorageRequest):
    """Set a localStorage item."""
    tab = get_current_tab()
    await tab.evaluate(f"localStorage.setItem('{req.key}', '{req.value}')")
    return {"success": True}


# Tab management endpoints

@app.post("/new_tab")
async def new_tab(req: NewTabRequest):
    """Create a new tab."""
    global current_tab_id, tabs, browser

    url = req.url or "about:blank"
    tab = await browser.get(url, new_tab=True)
    tab_id = generate_tab_id()
    tabs[tab_id] = tab
    current_tab_id = tab_id
    return {"tab_id": tab_id, "url": tab.url}


@app.post("/switch_tab")
async def switch_tab(req: SwitchTabRequest):
    """Switch to a different tab."""
    global current_tab_id

    if req.tab_id not in tabs:
        raise HTTPException(status_code=404, detail=f"Tab not found: {req.tab_id}")
    current_tab_id = req.tab_id
    tab = tabs[req.tab_id]
    await tab.activate()
    return {"success": True, "url": tab.url}


@app.post("/close_tab")
async def close_tab(req: CloseTabRequest):
    """Close a tab."""
    global current_tab_id, tabs

    if req.tab_id not in tabs:
        raise HTTPException(status_code=404, detail=f"Tab not found: {req.tab_id}")
    if len(tabs) <= 1:
        raise HTTPException(status_code=400, detail="Cannot close the last tab")

    tab = tabs.pop(req.tab_id)
    await tab.close()

    if current_tab_id == req.tab_id:
        current_tab_id = next(iter(tabs))

    return {"success": True}


@app.get("/list_tabs")
async def list_tabs():
    """List all tabs."""
    return {
        "tabs": [
            {"id": tab_id, "url": tab.url, "current": tab_id == current_tab_id}
            for tab_id, tab in tabs.items()
        ]
    }


# Network endpoints

@app.post("/intercept_requests")
async def intercept_requests(req: InterceptRequest):
    """Set up request interception (limited support in nodriver)."""
    # Note: nodriver has limited network interception support
    # This is a placeholder for future implementation
    return {"success": True, "note": "Limited support in nodriver"}


@app.get("/get_network_logs")
async def get_network_logs():
    """Get network request logs."""
    return {"logs": network_logs}


# File endpoints

@app.post("/upload_file")
async def upload_file(req: UploadFileRequest):
    """Upload a file to an input element."""
    tab = get_current_tab()
    element = await tab.select(req.selector)
    if not element:
        raise HTTPException(status_code=404, detail=f"Element not found: {req.selector}")

    # Use CDP to set files
    await element.send_file(req.file_path)
    return {"success": True}


@app.post("/download_file")
async def download_file(req: DownloadFileRequest):
    """Download a file from URL."""
    import httpx

    download_dir = "/tmp/downloads"
    os.makedirs(download_dir, exist_ok=True)

    async with httpx.AsyncClient() as client:
        response = await client.get(req.url, follow_redirects=True)
        filename = req.url.split("/")[-1] or "download"
        filepath = os.path.join(download_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

    return {"path": filepath}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
