import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryMessage(BaseModel):
    """Memory message payload."""

    role: str = Field(..., description="Role of the message.")
    content: str = Field(..., description="Message content.")


class MemoryConfigureRequest(BaseModel):
    """Request to configure memory backend."""

    enabled: bool | None = Field(
        default=None,
        description="Whether memory is enabled.",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Mem0 configuration payload.",
    )


class MemoryCreateRequest(BaseModel):
    """Request to create memories."""

    messages: list[MemoryMessage] = Field(
        ...,
        min_length=1,
        description="Conversation messages used to extract and store memories.",
    )
    run_id: str | None = None
    metadata: dict[str, Any] | None = None
    # Optional multi-tenant scope:
    # - "user" (default): per-sender zone, written under the
    #   caller's user_id.
    # - "server": Poco server zone, written under
    #   ``app_id=f"server:{memory_server_id}"`` so the memory backend
    #   can index it for cross-user shared search.
    # - "both": two writes are produced — one user-scope and one
    #   server-scope — so future searches with scope="both" can
    #   merge them via an OR filter.
    memory_scope: str | None = None
    memory_server_id: uuid.UUID | None = None


class MemorySearchRequest(BaseModel):
    """Request to search memories."""

    query: str = Field(..., description="Search query.")
    run_id: str | None = None
    filters: dict[str, Any] | None = None


class MemoryUpdateRequest(BaseModel):
    """Request to update a memory."""

    text: str = Field(..., min_length=1, description="Updated memory text.")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata for update operations.",
    )


class InternalMemoryCreateRequest(BaseModel):
    """Internal request to create memories by session scope."""

    messages: list[MemoryMessage] = Field(
        ...,
        min_length=1,
        description="Conversation messages used to extract and store memories.",
    )
    metadata: dict[str, Any] | None = None
    # Optional multi-tenant scope: "user" (default), "server" (Poco
    # server zone) or "both" (combine). Only honored when the session
    # is anchored to a Poco server via a bound IM channel.
    memory_scope: str | None = None
    memory_server_id: uuid.UUID | None = None


class InternalMemorySearchRequest(BaseModel):
    """Internal request to search memories by session scope."""

    query: str = Field(..., description="Search query.")
    filters: dict[str, Any] | None = None
    memory_scope: str | None = None
    memory_server_id: uuid.UUID | None = None


class InternalMemoryUpdateRequest(BaseModel):
    """Internal request to update memory by session scope."""

    text: str = Field(..., min_length=1, description="Updated memory text.")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata for update operations.",
    )
    memory_scope: str | None = None
    memory_server_id: uuid.UUID | None = None


class MemoryCreateJobEnqueueResponse(BaseModel):
    """Response for enqueueing a memory creation job."""

    job_id: uuid.UUID
    status: str


class MemoryCreateJobResponse(BaseModel):
    """Status response for a memory creation job."""

    job_id: uuid.UUID
    status: str
    progress: int = 0
    result: Any | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
