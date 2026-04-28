"""Live file-system and network monitoring for the Aegis-AI dashboard."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ModuleNotFoundError:
    FileSystemEvent = Any

    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass

    Observer = None

from config import Settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _CreatedFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        callback: Callable[[Path, dict[str, Any]], Awaitable[None]],
        watch_config: dict[str, Any],
    ) -> None:
        self.loop = loop
        self.callback = callback
        self.watch_config = watch_config

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        extensions = {item.lower() for item in self.watch_config.get("extensions", [])}
        if extensions and path.suffix.lower() not in extensions:
            return
        asyncio.run_coroutine_threadsafe(self.callback(path, self.watch_config), self.loop)


class WatchFolderManager:
    """Manage multiple watchdog observers for configured folders."""

    def __init__(
        self,
        settings: Settings,
        callback: Callable[[Path, dict[str, Any]], Awaitable[None]],
    ) -> None:
        self.settings = settings
        self.callback = callback
        self.loop: asyncio.AbstractEventLoop | None = None
        self.observer = Observer() if Observer is not None else None
        self._folders: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        if self.observer is not None:
            self.observer.start()

    async def stop(self) -> None:
        if self.observer is not None and self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

    async def add_folder(self, watch_config: dict[str, Any]) -> None:
        if self.observer is None:
            return
        if self.loop is None:
            self.loop = asyncio.get_running_loop()

        path = Path(watch_config["path"])
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        key = str(path.resolve()).lower()
        if key in self._folders:
            return

        handler = _CreatedFileHandler(self.loop, self.callback, watch_config)
        watch = self.observer.schedule(
            handler,
            str(path),
            recursive=bool(watch_config.get("recursive", True)),
        )
        self._folders[key] = {"watch_config": watch_config, "watch": watch}

    async def remove_folder(self, path: str) -> None:
        if self.observer is None:
            return
        key = str(Path(path).resolve()).lower()
        current = self._folders.pop(key, None)
        if current is not None:
            self.observer.unschedule(current["watch"])

    async def sync_folders(self, folders: list[dict[str, Any]]) -> None:
        wanted = {str(Path(item["path"]).resolve()).lower(): item for item in folders}
        current = set(self._folders.keys())
        for key in current - set(wanted):
            await self.remove_folder(self._folders[key]["watch_config"]["path"])
        for item in wanted.values():
            await self.add_folder(item)


class NetworkMonitor:
    """Poll active connections and emit events for newly observed outbound flows."""

    def __init__(
        self,
        settings: Settings,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self.settings = settings
        self.callback = callback
        self._seen: set[tuple[Any, ...]] = set()
        self._stop = asyncio.Event()

    async def run(self) -> None:
        if psutil is None:
            return
        while not self._stop.is_set():
            current: set[tuple[Any, ...]] = set()
            for connection in psutil.net_connections(kind="inet"):
                if not connection.raddr or connection.pid is None:
                    continue
                status = str(connection.status or "")
                key = (
                    connection.pid,
                    getattr(connection.laddr, "ip", ""),
                    getattr(connection.laddr, "port", 0),
                    getattr(connection.raddr, "ip", ""),
                    getattr(connection.raddr, "port", 0),
                    status,
                )
                current.add(key)
                if key in self._seen:
                    continue
                try:
                    process = psutil.Process(connection.pid)
                    process_name = process.name()
                except Exception:
                    process_name = "unknown"

                event = {
                    "id": f"net-{connection.pid}-{getattr(connection.raddr, 'ip', 'na')}-{getattr(connection.raddr, 'port', 0)}",
                    "event_type": "network_connection",
                    "created_at": utc_now(),
                    "pid": connection.pid,
                    "process_name": process_name,
                    "local_ip": getattr(connection.laddr, "ip", ""),
                    "local_port": getattr(connection.laddr, "port", 0),
                    "remote_ip": getattr(connection.raddr, "ip", ""),
                    "remote_port": getattr(connection.raddr, "port", 0),
                    "status": status,
                    "direction": "outbound",
                }
                await self.callback(event)
            self._seen = current
            await asyncio.sleep(self.settings.network_poll_seconds)

    async def stop(self) -> None:
        self._stop.set()
