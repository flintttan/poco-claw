import asyncio
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk.client import ClaudeSDKClient
from claude_agent_sdk.types import PermissionResultDeny

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class ToolPermissionController:
    """Stable SDK callback that delegates to the current lease holder."""

    def __init__(self) -> None:
        self._delegate: Any | None = None

    def set_delegate(self, delegate: Any) -> None:
        self._delegate = delegate

    def clear_delegate(self, delegate: Any) -> None:
        if self._delegate is delegate:
            self._delegate = None

    async def can_use_tool(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        context: Any,
    ) -> Any:
        delegate = self._delegate
        if delegate is None:
            return PermissionResultDeny(
                message="No active permission delegate for cached SDK client"
            )
        return await delegate.can_use_tool(tool_name, input_data, context)


@dataclass
class _ClientEntry:
    key: str
    fingerprint: str
    client: ClaudeSDKClient
    controller: ToolPermissionController
    lock: asyncio.Lock
    created_at: float
    last_used_at: float


class ClaudeSDKClientLease:
    def __init__(
        self,
        *,
        pool: "ClaudeSDKClientPool",
        entry: _ClientEntry,
        delegate: Any,
        cache_hit: bool,
        disconnect_on_release: bool,
    ) -> None:
        self._pool = pool
        self._entry = entry
        self._delegate = delegate
        self.cache_hit = cache_hit
        self.disconnect_on_release = disconnect_on_release
        self.client = entry.client
        self.controller = entry.controller
        self._invalidated = False

    def invalidate(self) -> None:
        self._invalidated = True

    async def __aenter__(self) -> "ClaudeSDKClientLease":
        self.controller.set_delegate(self._delegate)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.controller.clear_delegate(self._delegate)
        await self._pool.release(self, invalidate=self._invalidated or exc is not None)
        return False


class ClaudeSDKClientPool:
    """Process-local ClaudeSDKClient cache with per-client serial leases."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        ttl_seconds: float | None = None,
        max_clients: int | None = None,
        client_factory: Callable[[Any], ClaudeSDKClient] | None = None,
    ) -> None:
        self.enabled = (
            _env_bool("EXECUTOR_SDK_CLIENT_CACHE_ENABLED", True)
            if enabled is None
            else enabled
        )
        self.ttl_seconds = (
            max(1.0, _env_float("EXECUTOR_SDK_CLIENT_CACHE_TTL_SECONDS", 900.0))
            if ttl_seconds is None
            else ttl_seconds
        )
        self.max_clients = (
            max(1, _env_int("EXECUTOR_SDK_CLIENT_CACHE_MAX_CLIENTS", 16))
            if max_clients is None
            else max_clients
        )
        self._client_factory = client_factory or (
            lambda options: ClaudeSDKClient(options=options)
        )
        self._entries: dict[str, _ClientEntry] = {}
        self._entries_lock = asyncio.Lock()

    async def acquire(
        self,
        *,
        key: str | None,
        fingerprint: str,
        options_factory: Callable[[ToolPermissionController], Any],
        delegate: Any,
    ) -> ClaudeSDKClientLease:
        if not self.enabled or not key:
            controller = ToolPermissionController()
            client = self._client_factory(options_factory(controller))
            await client.connect()
            entry = _ClientEntry(
                key=key or "__uncached__",
                fingerprint=fingerprint,
                client=client,
                controller=controller,
                lock=asyncio.Lock(),
                created_at=time.monotonic(),
                last_used_at=time.monotonic(),
            )
            await entry.lock.acquire()
            return ClaudeSDKClientLease(
                pool=self,
                entry=entry,
                delegate=delegate,
                cache_hit=False,
                disconnect_on_release=True,
            )

        while True:
            async with self._entries_lock:
                await self._evict_expired_locked()
                entry = self._entries.get(key)
                cache_hit = entry is not None
                if entry is None or (
                    entry.fingerprint != fingerprint and not entry.lock.locked()
                ):
                    if entry is not None:
                        await self._disconnect_entry(entry)
                    controller = ToolPermissionController()
                    client = self._client_factory(options_factory(controller))
                    await client.connect()
                    now = time.monotonic()
                    entry = _ClientEntry(
                        key=key,
                        fingerprint=fingerprint,
                        client=client,
                        controller=controller,
                        lock=asyncio.Lock(),
                        created_at=now,
                        last_used_at=now,
                    )
                    self._entries[key] = entry
                    cache_hit = False
                    await self._enforce_max_clients_locked()

            await entry.lock.acquire()

            async with self._entries_lock:
                if self._entries.get(key) is not entry:
                    entry.lock.release()
                    continue

                if entry.fingerprint != fingerprint:
                    await self._disconnect_entry(entry)
                    self._entries.pop(key, None)
                    entry.lock.release()
                    continue

                if not self._is_client_healthy(entry.client):
                    await self._disconnect_entry(entry)
                    self._entries.pop(key, None)
                    entry.lock.release()
                    continue

                return ClaudeSDKClientLease(
                    pool=self,
                    entry=entry,
                    delegate=delegate,
                    cache_hit=cache_hit,
                    disconnect_on_release=False,
                )

    async def release(self, lease: ClaudeSDKClientLease, *, invalidate: bool) -> None:
        entry = lease._entry
        try:
            if lease.disconnect_on_release:
                await self._disconnect_entry(entry)
                return

            entry.last_used_at = time.monotonic()
            if invalidate:
                async with self._entries_lock:
                    if self._entries.get(entry.key) is entry:
                        self._entries.pop(entry.key, None)
                await self._disconnect_entry(entry)
        finally:
            if entry.lock.locked():
                entry.lock.release()

    async def close(self) -> None:
        async with self._entries_lock:
            entries = list(self._entries.values())
            self._entries.clear()
        for entry in entries:
            await self._disconnect_entry(entry)

    async def _evict_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [
            key
            for key, entry in self._entries.items()
            if not entry.lock.locked() and now - entry.last_used_at > self.ttl_seconds
        ]
        for key in expired:
            entry = self._entries.pop(key)
            await self._disconnect_entry(entry)
            logger.info("sdk_client_cache_evicted", extra={"cache_key": key})

    async def _enforce_max_clients_locked(self) -> None:
        while len(self._entries) > self.max_clients:
            idle_entries = [
                entry for entry in self._entries.values() if not entry.lock.locked()
            ]
            if not idle_entries:
                return
            oldest = min(idle_entries, key=lambda entry: entry.last_used_at)
            self._entries.pop(oldest.key, None)
            await self._disconnect_entry(oldest)
            logger.info("sdk_client_cache_evicted", extra={"cache_key": oldest.key})

    async def _disconnect_entry(self, entry: _ClientEntry) -> None:
        try:
            await entry.client.disconnect()
        except Exception:
            logger.warning(
                "sdk_client_disconnect_failed",
                extra={"cache_key": entry.key},
                exc_info=True,
            )

    @staticmethod
    def _is_client_healthy(client: ClaudeSDKClient) -> bool:
        return bool(
            getattr(client, "_query", None) and getattr(client, "_transport", None)
        )


_pool: ClaudeSDKClientPool | None = None


def get_claude_sdk_client_pool() -> ClaudeSDKClientPool:
    global _pool
    if _pool is None:
        _pool = ClaudeSDKClientPool()
    return _pool
