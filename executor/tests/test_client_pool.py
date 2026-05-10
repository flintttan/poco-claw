import asyncio
import unittest
from typing import Any, Callable, cast

from claude_agent_sdk.client import ClaudeSDKClient
from app.core.client_pool import ClaudeSDKClientPool


class FakeClient:
    def __init__(self, options):
        self.options = options
        self.connected = False
        self.disconnected = False
        self._query = None
        self._transport = None

    async def connect(self) -> None:
        self.connected = True
        self._query = object()
        self._transport = object()

    async def disconnect(self) -> None:
        self.disconnected = True
        self._query = None
        self._transport = None


class Delegate:
    async def can_use_tool(self, tool_name, input_data, context):
        return {"tool_name": tool_name, "input": input_data}


class ClaudeSDKClientPoolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.created: list[FakeClient] = []

    def _pool(self, *, enabled: bool = True) -> ClaudeSDKClientPool:
        def factory(options):
            client = FakeClient(options)
            self.created.append(client)
            return client

        return ClaudeSDKClientPool(
            enabled=enabled,
            ttl_seconds=60,
            max_clients=4,
            client_factory=cast(Callable[[Any], ClaudeSDKClient], factory),
        )

    async def test_reuses_healthy_client_for_same_key_and_fingerprint(self) -> None:
        pool = self._pool()

        def options_factory(controller):
            return {"controller": controller}

        async with await pool.acquire(
            key="agent:a:session:s",
            fingerprint="same",
            options_factory=options_factory,
            delegate=Delegate(),
        ) as first:
            first_client = cast(FakeClient, first.client)
            self.assertFalse(first.cache_hit)

        async with await pool.acquire(
            key="agent:a:session:s",
            fingerprint="same",
            options_factory=options_factory,
            delegate=Delegate(),
        ) as second:
            self.assertTrue(second.cache_hit)
            self.assertIs(second.client, first_client)

        await pool.close()

    async def test_serializes_same_cached_client(self) -> None:
        pool = self._pool()
        first_lease = await pool.acquire(
            key="agent:a:session:s",
            fingerprint="same",
            options_factory=lambda controller: {"controller": controller},
            delegate=Delegate(),
        )
        await first_lease.__aenter__()

        second_task = asyncio.create_task(
            pool.acquire(
                key="agent:a:session:s",
                fingerprint="same",
                options_factory=lambda controller: {"controller": controller},
                delegate=Delegate(),
            )
        )
        await asyncio.sleep(0)
        self.assertFalse(second_task.done())

        await first_lease.__aexit__(None, None, None)
        second_lease = await second_task
        async with second_lease:
            self.assertTrue(second_lease.cache_hit)

        await pool.close()

    async def test_rebuilds_unhealthy_cached_client(self) -> None:
        pool = self._pool()

        def options_factory(controller):
            return {"controller": controller}

        async with await pool.acquire(
            key="agent:a:session:s",
            fingerprint="same",
            options_factory=options_factory,
            delegate=Delegate(),
        ) as first:
            first_client = cast(FakeClient, first.client)

        first_client._query = None
        async with await pool.acquire(
            key="agent:a:session:s",
            fingerprint="same",
            options_factory=options_factory,
            delegate=Delegate(),
        ) as second:
            self.assertIsNot(second.client, first_client)
            self.assertTrue(first_client.disconnected)
            self.assertFalse(second.cache_hit)

        await pool.close()

    async def test_uncached_mode_disconnects_after_release(self) -> None:
        pool = self._pool(enabled=False)

        async with await pool.acquire(
            key="agent:a:session:s",
            fingerprint="same",
            options_factory=lambda controller: {"controller": controller},
            delegate=Delegate(),
        ) as lease:
            client = cast(FakeClient, lease.client)
            self.assertTrue(client.connected)
            self.assertTrue(lease.disconnect_on_release)

        self.assertTrue(client.disconnected)


if __name__ == "__main__":
    unittest.main()
