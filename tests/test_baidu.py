"""Test browser session with Baidu."""

import base64
import pytest

from nodriver_mcp.session_manager import get_session_manager


@pytest.fixture(scope="function")
async def session():
    """Create and cleanup a browser session."""
    manager = get_session_manager()
    session_id = await manager.create_session(headless=True)
    yield session_id, manager
    await manager.destroy_session(session_id)


@pytest.mark.asyncio
async def test_navigate_to_baidu(session):
    """Test navigating to Baidu and getting content."""
    session_id, manager = session

    # Navigate
    result = await manager.request(
        session_id, "POST", "/navigate",
        json={"url": "https://www.baidu.com"}
    )
    assert "baidu.com" in result.get("url", "")

    # Check URL
    url_result = await manager.request(session_id, "GET", "/get_url")
    assert "baidu.com" in url_result.get("url", "")

    # Get text
    text_result = await manager.request(
        session_id, "POST", "/get_text",
        json={"selector": None}
    )
    text = text_result.get("text", "")
    assert len(text) > 0
    assert "百度" in text

    # Take screenshot
    screenshot_result = await manager.request(
        session_id, "POST", "/screenshot",
        json={"full_page": False}
    )
    assert screenshot_result.get("image") is not None
    img_data = base64.b64decode(screenshot_result["image"])
    assert len(img_data) > 1000  # Should be a valid image
