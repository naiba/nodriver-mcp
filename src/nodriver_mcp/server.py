"""MCP Server entry point for nodriver browser automation."""

import asyncio
import logging
import signal
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .session_manager import get_session_manager
from .tools import register_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_server():
    """Run the MCP server."""
    server = Server("nodriver-mcp")
    manager = get_session_manager()

    # Register all tools
    register_tools(server)

    # Start cleanup task
    await manager.start_cleanup_task()

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        logger.info("Starting nodriver-mcp server")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        logger.info("Cleaning up sessions...")
        await manager.cleanup_all()
        logger.info("Server stopped")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
