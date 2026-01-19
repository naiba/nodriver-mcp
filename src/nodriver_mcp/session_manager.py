"""Docker container lifecycle management for browser sessions."""

import asyncio
import atexit
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

import docker
import httpx
from docker.errors import NotFound
from docker.models.containers import Container

logger = logging.getLogger(__name__)

# Docker image name for browser containers
IMAGE_NAME = "nodriver-mcp-browser"

# Port range for container allocation
PORT_START = 9001
PORT_END = 9999

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 30 * 60


@dataclass
class SessionInfo:
    """Information about a browser session."""

    session_id: str
    container: Container
    port: int
    created_at: datetime
    last_used: datetime = field(default_factory=datetime.now)
    headless: bool = True

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.port}"

    def touch(self):
        """Update last used timestamp."""
        self.last_used = datetime.now()

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return (datetime.now() - self.last_used).total_seconds() > SESSION_TIMEOUT


class SessionManager:
    """Manages Docker containers for browser sessions."""

    def __init__(self):
        self.sessions: dict[str, SessionInfo] = {}
        self.used_ports: set[int] = set()
        self.port_counter = PORT_START
        self.docker_client = docker.from_env()
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # Register cleanup on exit
        atexit.register(self._sync_cleanup_all)

    def _allocate_port(self) -> int:
        """Allocate an available port."""
        while self.port_counter in self.used_ports:
            self.port_counter += 1
            if self.port_counter > PORT_END:
                self.port_counter = PORT_START

        port = self.port_counter
        self.used_ports.add(port)
        self.port_counter += 1
        return port

    def _release_port(self, port: int):
        """Release a port back to the pool."""
        self.used_ports.discard(port)

    async def _wait_healthy(self, port: int, timeout: int = 60) -> bool:
        """Wait for container to become healthy."""
        url = f"http://localhost:{port}/health"
        start_time = datetime.now()

        async with httpx.AsyncClient() as client:
            while (datetime.now() - start_time).total_seconds() < timeout:
                try:
                    response = await client.get(url, timeout=5)
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)

        return False

    async def create_session(self, headless: bool = True) -> str:
        """Create a new browser session in a Docker container."""
        async with self._lock:
            session_id = uuid4().hex[:8]
            port = self._allocate_port()

            try:
                container = self.docker_client.containers.run(
                    IMAGE_NAME,
                    detach=True,
                    ports={"9000/tcp": port},
                    shm_size="2g",
                    environment={
                        "HEADLESS": str(headless).lower(),
                        "PORT": "9000",
                    },
                    name=f"nodriver-{session_id}",
                    remove=True,  # Auto-remove on stop
                )

                # Wait for container to be healthy
                if not await self._wait_healthy(port):
                    container.stop()
                    self._release_port(port)
                    raise RuntimeError("Container failed to become healthy")

                session_info = SessionInfo(
                    session_id=session_id,
                    container=container,
                    port=port,
                    created_at=datetime.now(),
                    headless=headless,
                )
                self.sessions[session_id] = session_info

                logger.info(f"Created session {session_id} on port {port}")
                return session_id

            except Exception as e:
                self._release_port(port)
                raise RuntimeError(f"Failed to create session: {e}") from e

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy a browser session and its container."""
        async with self._lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions.pop(session_id)
            self._release_port(session.port)

            try:
                session.container.stop(timeout=10)
            except NotFound:
                pass  # Already removed
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")

            logger.info(f"Destroyed session {session_id}")
            return True

    def get_session(self, session_id: str) -> SessionInfo | None:
        """Get session info by ID."""
        session = self.sessions.get(session_id)
        if session:
            session.touch()
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions."""
        result = []
        for session in self.sessions.values():
            result.append({
                "id": session.session_id,
                "port": session.port,
                "created_at": session.created_at.isoformat(),
                "last_used": session.last_used.isoformat(),
                "headless": session.headless,
                "base_url": session.base_url,
            })
        return result

    async def request(
        self,
        session_id: str,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a request to a session's container."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        url = f"{session.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=60) as client:
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            else:
                response = await client.post(url, **kwargs)

            if response.status_code >= 400:
                error_detail = response.json().get("detail", response.text)
                raise RuntimeError(f"Container request failed: {error_detail}")

            return response.json()

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired()
        ]
        for session_id in expired:
            await self.destroy_session(session_id)
            logger.info(f"Cleaned up expired session {session_id}")

    async def start_cleanup_task(self):
        """Start background task to clean up expired sessions."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Check every minute
                await self.cleanup_expired_sessions()

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_task(self):
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def cleanup_all(self):
        """Clean up all sessions."""
        await self.stop_cleanup_task()
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.destroy_session(session_id)

    def _sync_cleanup_all(self):
        """Synchronous cleanup for atexit handler."""
        for session in list(self.sessions.values()):
            try:
                session.container.stop(timeout=5)
            except Exception:
                pass
        self.sessions.clear()


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
