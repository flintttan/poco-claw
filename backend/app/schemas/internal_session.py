from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class InternalSessionStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=50)


class SessionCancellationClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=255)
    lease_seconds: int = Field(default=30, ge=1, le=3600)


class SessionCancellationClaimResponse(BaseModel):
    session_id: UUID
    run_id: UUID | None = None
    worker_id: str | None = None
    reason: str | None = None
    requested_at: datetime


class SessionCancellationCompleteRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=255)
    stop_status: Literal["stopped", "not_found", "failed"]
    message: str | None = None


class SessionCancellationCompleteResponse(BaseModel):
    session_id: UUID
    status: str
    stop_status: Literal["stopped", "not_found", "failed"]
    canceled_runs: int = 0
