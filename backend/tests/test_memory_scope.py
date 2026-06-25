"""Tests for the multi-zone memory scope (per-user vs. per-server).

Covers the C1 fix:
- ``MemoryCreateRequest.memory_scope="server"`` writes the memory
  under ``app_id="poco-server:<id>"`` (drops ``user_id``).
- ``memory_scope="both"`` does two writes — one user-scope and one
  server-scope — so future scope=both searches can OR them back.
- ``MemoryService.search_memories`` for scope="server" applies the
  matching ``app_id`` filter; scope="both" merges ``user_id`` and
  ``app_id`` via an OR filter. Before the fix, the search filter was
  keyed on ``server_id`` (which mem0 never persisted), so the server
  branch always returned empty.

These tests use a fake memory backend; the goal is to prove that the
backend call shape is correct, not to exercise mem0.
"""

from __future__ import annotations

import unittest
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

from app.schemas.memory import (
    MemoryCreateRequest,
    MemoryMessage,
    MemorySearchRequest,
)
from app.services.memory_service import (
    DEFAULT_MEMORY_AGENT_ID,
    MemoryService,
    _server_app_id,
)


class _FakeMemoryBackend:
    """Minimal stub that records every add()/search() call."""

    def __init__(self) -> None:
        self.add_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []

    def add(self, **kwargs: Any) -> dict[str, Any]:
        self.add_calls.append(kwargs)
        return {"id": f"mem-{len(self.add_calls)}"}

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.search_calls.append(kwargs)
        return {"results": []}

    def get(self, memory_id: str) -> dict[str, Any]:
        return {"id": memory_id}


def _messages() -> list[MemoryMessage]:
    return [
        MemoryMessage(role="user", content="hi"),
        MemoryMessage(role="assistant", content="hello"),
    ]


def _service_with_fake() -> tuple[MemoryService, _FakeMemoryBackend]:
    fake = _FakeMemoryBackend()
    service = MemoryService()
    service._enabled = True  # bypass real config check
    service._instance = fake
    return service, fake


class ServerAppIdHelperTests(unittest.TestCase):
    def test_server_app_id_prefix(self) -> None:
        server_id = "11111111-2222-3333-4444-555555555555"
        self.assertEqual(
            _server_app_id(server_id),
            f"poco-server:{server_id}",
        )

    def test_server_app_id_works_with_uuid_object(self) -> None:
        server_id = uuid.uuid4()
        self.assertEqual(
            _server_app_id(server_id),
            f"poco-server:{server_id}",
        )


class CreateScopeTests(unittest.TestCase):
    def test_user_scope_default_writes_under_user_id(self) -> None:
        service, fake = _service_with_fake()
        request = MemoryCreateRequest(
            messages=_messages(),
            memory_scope=None,  # default
            memory_server_id=None,
        )
        service.create_memories(user_id="u-1", request=request)

        self.assertEqual(len(fake.add_calls), 1)
        call = fake.add_calls[0]
        self.assertEqual(call["user_id"], "u-1")
        self.assertEqual(call["agent_id"], DEFAULT_MEMORY_AGENT_ID)
        self.assertNotIn("app_id", call)

    def test_user_scope_explicit_writes_under_user_id(self) -> None:
        service, fake = _service_with_fake()
        request = MemoryCreateRequest(
            messages=_messages(),
            memory_scope="user",
            memory_server_id=uuid.uuid4(),
        )
        service.create_memories(user_id="u-1", request=request)

        self.assertEqual(len(fake.add_calls), 1)
        call = fake.add_calls[0]
        self.assertEqual(call["user_id"], "u-1")
        self.assertNotIn("app_id", call)

    def test_server_scope_drops_user_id_and_sets_app_id(self) -> None:
        service, fake = _service_with_fake()
        server_id = uuid.uuid4()
        request = MemoryCreateRequest(
            messages=_messages(),
            memory_scope="server",
            memory_server_id=server_id,
        )
        service.create_memories(user_id="u-1", request=request)

        self.assertEqual(len(fake.add_calls), 1)
        call = fake.add_calls[0]
        self.assertNotIn("user_id", call)
        self.assertEqual(call["app_id"], f"poco-server:{server_id}")
        self.assertEqual(call["agent_id"], DEFAULT_MEMORY_AGENT_ID)

    def test_both_scope_writes_user_and_server_records(self) -> None:
        service, fake = _service_with_fake()
        server_id = uuid.uuid4()
        request = MemoryCreateRequest(
            messages=_messages(),
            memory_scope="both",
            memory_server_id=server_id,
        )
        service.create_memories(user_id="u-1", request=request)

        # Two writes: one user-scope, one server-scope. They must
        # travel separately so a scope="both" search can OR them
        # back together.
        self.assertEqual(len(fake.add_calls), 2)

        user_call, server_call = fake.add_calls
        self.assertEqual(user_call["user_id"], "u-1")
        self.assertNotIn("app_id", user_call)

        self.assertNotIn("user_id", server_call)
        self.assertEqual(server_call["app_id"], f"poco-server:{server_id}")


class SearchScopeTests(unittest.TestCase):
    def test_user_scope_search_uses_user_id(self) -> None:
        service, fake = _service_with_fake()
        request = MemorySearchRequest(query="hello")
        service.search_memories(user_id="u-1", request=request, memory_scope="user")

        self.assertEqual(len(fake.search_calls), 1)
        call = fake.search_calls[0]
        self.assertEqual(call["user_id"], "u-1")
        self.assertEqual(call["query"], "hello")
        self.assertNotIn("filters", call)

    def test_server_scope_search_filters_by_app_id(self) -> None:
        service, fake = _service_with_fake()
        server_id = uuid.uuid4()
        request = MemorySearchRequest(query="hello")
        service.search_memories(
            user_id="u-1",
            request=request,
            memory_scope="server",
            memory_server_id=server_id,
        )

        self.assertEqual(len(fake.search_calls), 1)
        call = fake.search_calls[0]
        # The server-scope branch must NOT carry user_id (otherwise
        # mem0 would scope to that user and the app_id filter would
        # be a no-op).
        self.assertNotIn("user_id", call)
        self.assertEqual(
            call["filters"],
            {"app_id": f"poco-server:{server_id}"},
        )

    def test_both_scope_search_merges_user_and_server_via_or(self) -> None:
        service, fake = _service_with_fake()
        server_id = uuid.uuid4()
        request = MemorySearchRequest(query="hello")
        service.search_memories(
            user_id="u-1",
            request=request,
            memory_scope="both",
            memory_server_id=server_id,
        )

        self.assertEqual(len(fake.search_calls), 1)
        call = fake.search_calls[0]
        self.assertEqual(call["query"], "hello")
        self.assertEqual(call["user_id"], "u-1")
        self.assertEqual(
            call["filters"],
            {
                "OR": [
                    {"user_id": "u-1"},
                    {"app_id": f"poco-server:{server_id}"},
                ],
            },
        )

    def test_user_scope_search_merges_with_caller_filters(self) -> None:
        service, fake = _service_with_fake()
        request = MemorySearchRequest(
            query="hello",
            filters={"category": "preferences"},
        )
        service.search_memories(user_id="u-1", request=request, memory_scope="user")

        self.assertEqual(len(fake.search_calls), 1)
        call = fake.search_calls[0]
        self.assertEqual(
            call["filters"],
            {"category": "preferences"},
        )


class MemoryScopeDisabledGuardTests(unittest.TestCase):
    """Verify the disabled-memory guardrail survives the refactor."""

    def test_create_memories_raises_when_disabled(self) -> None:
        from app.core.errors.exceptions import AppException

        service = MemoryService()
        service._enabled = False
        request = MemoryCreateRequest(messages=_messages())

        with self.assertRaises(AppException):
            service.create_memories(user_id="u-1", request=request)


class MemoryCreateJobScopePassthroughTests(unittest.TestCase):
    """``process_create_job`` must pull scope from job metadata and pass
    it through to the memory service as first-class fields. The job
    processor is synchronous (it runs in FastAPI BackgroundTasks)."""

    def test_scope_extracted_from_metadata(self) -> None:
        import uuid as _uuid

        from app.services.memory_create_job_service import MemoryCreateJobService

        server_id = _uuid.uuid4()
        fake_backend = MagicMock()
        fake_backend.add = MagicMock(return_value={"id": "m-1"})

        service = MemoryService()
        service._enabled = True
        service._instance = fake_backend

        job_service = MemoryCreateJobService(memory_service=service)

        job = MagicMock()
        job.id = _uuid.uuid4()
        job.user_id = "u-1"
        job.messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        job.run_id = None
        job.request_metadata = {
            "memory_scope": "server",
            "memory_server_id": str(server_id),
        }
        job.status = "queued"

        with patch(
            "app.services.memory_create_job_service.MemoryCreateJobRepository.get_by_id",
            return_value=job,
        ):
            # process_create_job is sync (FastAPI BackgroundTasks).
            job_service.process_create_job(job.id)

        # The fake backend should have been called with the scope
        # fields extracted from metadata (not embedded in metadata).
        fake_backend.add.assert_called_once()
        call_kwargs = fake_backend.add.call_args.kwargs
        self.assertNotIn("user_id", call_kwargs)
        self.assertEqual(call_kwargs["app_id"], f"poco-server:{server_id}")

    def test_user_scope_metadata_uses_user_id(self) -> None:
        """Negative control: when scope is "user", the create must
        use user_id (the original owner) and NOT include app_id."""

        from app.services.memory_create_job_service import MemoryCreateJobService

        fake_backend = MagicMock()
        fake_backend.add = MagicMock(return_value={"id": "m-1"})

        service = MemoryService()
        service._enabled = True
        service._instance = fake_backend

        job_service = MemoryCreateJobService(memory_service=service)

        job = MagicMock()
        job.id = uuid.uuid4()
        job.user_id = "u-1"
        job.messages = [{"role": "user", "content": "hi"}]
        job.run_id = None
        job.request_metadata = {
            "memory_scope": "user",
            "memory_server_id": str(uuid.uuid4()),
        }
        job.status = "queued"

        with patch(
            "app.services.memory_create_job_service.MemoryCreateJobRepository.get_by_id",
            return_value=job,
        ):
            job_service.process_create_job(job.id)

        fake_backend.add.assert_called_once()
        call_kwargs = fake_backend.add.call_args.kwargs
        self.assertEqual(call_kwargs["user_id"], "u-1")
        self.assertNotIn("app_id", call_kwargs)


if __name__ == "__main__":
    unittest.main()
