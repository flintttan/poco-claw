"""Pydantic schemas for the IM binding (Connected Accounts) endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.user_profile import UserPublicProfileResponse


class BindingCodeCreateRequest(BaseModel):
    provider: Literal["feishu", "dingtalk", "telegram"] | None = Field(
        default=None,
        description=(
            "Optional provider scope. When set, the code can only be "
            "consumed by messages from that provider."
        ),
    )


class BindingCodeResponse(BaseModel):
    code: str
    provider: str | None = None
    expires_at: datetime
    ttl_seconds: int


class ImBindingResponse(BaseModel):
    id: int
    provider: str
    im_user_id: str
    im_union_id: str | None = None
    im_display_name: str | None = None
    bound_via: str
    bound_at: datetime
    last_seen_at: datetime | None = None


class ServerImChannelResponse(BaseModel):
    """One row in the server-detail page's "Linked IM chats" panel."""

    id: int
    provider: str
    destination: str
    chat_type: str
    enabled: bool
    last_bound_by_user_id: str | None = None
    last_bound_at: datetime | None = None
    last_bound_by_user: UserPublicProfileResponse | None = None


class ServerImChannelUpdateRequest(BaseModel):
    enabled: bool
