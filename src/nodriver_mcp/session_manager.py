"""Docker container lifecycle management for browser sessions."""

import asyncio
import atexit
import logging
import os
import random
import socket
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

# Container name prefix for identification
CONTAINER_PREFIX = "nodriver-"


def is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


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
        # Use random starting point to reduce collision probability
        self.port_counter = random.randint(PORT_START, PORT_END)
        self.docker_client = docker.from_env()
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        # Unique ID for this manager instance (for logging/debugging)
        self._manager_id = uuid4().hex[:6]

        # Discover existing nodriver containers and mark their ports as used
        self._discover_existing_containers()

        # Register cleanup on exit
        atexit.register(self._sync_cleanup_all)

        logger.info(f"SessionManager {self._manager_id} initialized, "
                    f"discovered {len(self.used_ports)} existing containers")

    def _discover_existing_containers(self):
        """Discover existing nodriver containers and mark their ports as used."""
        try:
            containers = self.docker_client.containers.list(
                filters={"name": CONTAINER_PREFIX}
            )
            for container in containers:
                # Extract port mapping from container
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                tcp_port_info = ports.get("9000/tcp")
                if tcp_port_info:
                    for binding in tcp_port_info:
                        host_port = int(binding.get("HostPort", 0))
                        if PORT_START <= host_port <= PORT_END:
                            self.used_ports.add(host_port)
                            logger.debug(f"Discovered existing container "
                                       f"{container.name} on port {host_port}")
        except Exception as e:
            logger.warning(f"Failed to discover existing containers: {e}")

    def _allocate_port(self) -> int:
        """Allocate an available port with actual availability check."""
        attempts = 0
        max_attempts = PORT_END - PORT_START + 1

        while attempts < max_attempts:
            # Skip ports we know are used
            while self.port_counter in self.used_ports:
                self.port_counter += 1
                if self.port_counter > PORT_END:
                    self.port_counter = PORT_START
                attempts += 1
                if attempts >= max_attempts:
                    break

            if attempts >= max_attempts:
                break

            port = self.port_counter
            self.port_counter += 1
            if self.port_counter > PORT_END:
                self.port_counter = PORT_START

            # Actually check if port is available on the system
            if is_port_available(port):
                self.used_ports.add(port)
                logger.debug(f"Manager {self._manager_id} allocated port {port}")
                return port
            else:
                # Port is used by something else, mark it and continue
                self.used_ports.add(port)
                logger.debug(f"Port {port} not available, trying next")
                attempts += 1

        raise RuntimeError("No available ports in the configured range")

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

    async def create_session(self, headless: bool = True, proxy: str | None = None) -> str:
        """Create a new browser session in a Docker container.

        Args:
            headless: Run browser in headless mode.
            proxy: Optional proxy server URL (e.g., "http://proxy:8080" or "socks5://proxy:1080").
        """
        max_retries = 3

        async with self._lock:
            # Re-discover containers before creating to get latest state
            self._discover_existing_containers()

            last_error = None
            for retry in range(max_retries):
                session_id = uuid4().hex[:8]
                port = self._allocate_port()
                container_name = f"{CONTAINER_PREFIX}{session_id}"

                try:
                    # Check if container name already exists (unlikely but possible)
                    try:
                        existing = self.docker_client.containers.get(container_name)
                        logger.warning(f"Container {container_name} already exists, "
                                     "generating new session_id")
                        continue
                    except NotFound:
                        pass  # Good, container doesn't exist

                    # Build environment variables
                    env = {
                        "HEADLESS": str(headless).lower(),
                        "PORT": "9000",
                    }
                    if proxy:
                        env["PROXY_SERVER"] = proxy

                    container = self.docker_client.containers.run(
                        IMAGE_NAME,
                        detach=True,
                        ports={"9000/tcp": port},
                        shm_size="2g",
                        environment=env,
                        name=container_name,
                        labels={
                            "nodriver.session_id": session_id,
                            "nodriver.manager_id": self._manager_id,
                            "nodriver.created_by": f"pid-{os.getpid()}",
                        },
                        remove=True,  # Auto-remove on stop
                    )

                    # Wait for container to be healthy
                    if not await self._wait_healthy(port):
                        try:
                            container.stop()
                        except Exception:
                            pass
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

                    logger.info(f"Manager {self._manager_id} created session "
                              f"{session_id} on port {port}")
                    return session_id

                except Exception as e:
                    self._release_port(port)
                    last_error = e
                    logger.warning(f"Retry {retry + 1}/{max_retries} failed: {e}")
                    # Re-discover containers in case state changed
                    self._discover_existing_containers()

            raise RuntimeError(f"Failed to create session after {max_retries} "
                             f"retries: {last_error}") from last_error

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy a browser session and its container."""
        async with self._lock:
            # First check if we have this session in memory
            if session_id in self.sessions:
                session = self.sessions.pop(session_id)
                self._release_port(session.port)

                try:
                    session.container.stop(timeout=10)
                except NotFound:
                    pass  # Already removed
                except Exception as e:
                    logger.warning(f"Error stopping container: {e}")

                logger.info(f"Manager {self._manager_id} destroyed session {session_id}")
                return True

            # Session not in memory, try to find container by name directly
            # This handles the case where another agent created the container
            container_name = f"{CONTAINER_PREFIX}{session_id}"
            try:
                container = self.docker_client.containers.get(container_name)
                # Get port before stopping
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                tcp_port_info = ports.get("9000/tcp")
                if tcp_port_info:
                    for binding in tcp_port_info:
                        host_port = int(binding.get("HostPort", 0))
                        self._release_port(host_port)

                container.stop(timeout=10)
                logger.info(f"Manager {self._manager_id} destroyed orphaned "
                          f"session {session_id}")
                return True
            except NotFound:
                logger.debug(f"Session {session_id} not found")
                return False
            except Exception as e:
                logger.warning(f"Error stopping orphaned container: {e}")
                return False

    def get_session(self, session_id: str) -> SessionInfo | None:
        """Get session info by ID (including sessions from other managers)."""
        # First check our local sessions
        session = self.sessions.get(session_id)
        if session:
            session.touch()
            return session

        # Try to find the container by name (created by another manager)
        container_name = f"{CONTAINER_PREFIX}{session_id}"
        try:
            container = self.docker_client.containers.get(container_name)

            # Get port from container
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            tcp_port_info = ports.get("9000/tcp")
            if not tcp_port_info:
                logger.warning(f"Container {container_name} has no port mapping")
                return None

            port = int(tcp_port_info[0].get("HostPort", 0))

            # Create a session info for this orphaned container
            # and adopt it into our local session management
            session_info = SessionInfo(
                session_id=session_id,
                container=container,
                port=port,
                created_at=datetime.fromisoformat(
                    container.attrs.get("Created", "").replace("Z", "+00:00")[:26]
                ) if container.attrs.get("Created") else datetime.now(),
                headless=True,  # Default, we can't know for sure
            )

            # Adopt this session
            self.sessions[session_id] = session_info
            self.used_ports.add(port)

            logger.info(f"Manager {self._manager_id} adopted orphaned "
                      f"session {session_id} on port {port}")
            return session_info

        except NotFound:
            return None
        except Exception as e:
            logger.warning(f"Error getting session {session_id}: {e}")
            return None

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions (including from other manager instances)."""
        result = []
        seen_ids = set()

        # First add sessions we manage directly (more detailed info)
        for session in self.sessions.values():
            seen_ids.add(session.session_id)
            result.append({
                "id": session.session_id,
                "port": session.port,
                "created_at": session.created_at.isoformat(),
                "last_used": session.last_used.isoformat(),
                "headless": session.headless,
                "base_url": session.base_url,
                "owned_by_this_manager": True,
            })

        # Then discover containers from other managers
        try:
            containers = self.docker_client.containers.list(
                filters={"name": CONTAINER_PREFIX}
            )
            for container in containers:
                # Extract session_id from container name
                name = container.name
                if name.startswith(CONTAINER_PREFIX):
                    session_id = name[len(CONTAINER_PREFIX):]
                    if session_id in seen_ids:
                        continue  # Already listed

                    # Get port from container
                    ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                    tcp_port_info = ports.get("9000/tcp")
                    port = None
                    if tcp_port_info:
                        port = int(tcp_port_info[0].get("HostPort", 0))

                    # Get labels for additional info
                    labels = container.labels or {}

                    result.append({
                        "id": session_id,
                        "port": port,
                        "created_at": container.attrs.get("Created", "unknown"),
                        "last_used": "unknown",
                        "headless": True,  # Default, can't know for sure
                        "base_url": f"http://localhost:{port}" if port else None,
                        "owned_by_this_manager": False,
                        "manager_id": labels.get("nodriver.manager_id", "unknown"),
                    })
        except Exception as e:
            logger.warning(f"Failed to list containers from Docker: {e}")

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
        """Synchronous cleanup for atexit handler.

        Only cleans up sessions that were created by this manager instance,
        not sessions adopted from other managers.
        """
        for session_id, session in list(self.sessions.items()):
            try:
                # Check if this container was created by us via labels
                labels = session.container.labels or {}
                if labels.get("nodriver.manager_id") == self._manager_id:
                    session.container.stop(timeout=5)
                    logger.debug(f"Cleaned up own session {session_id}")
                else:
                    logger.debug(f"Skipping cleanup of adopted session {session_id}")
            except NotFound:
                pass  # Already gone
            except Exception as e:
                logger.debug(f"Error during cleanup of {session_id}: {e}")
        self.sessions.clear()


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
