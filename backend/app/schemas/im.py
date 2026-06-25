from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass(slots=True)
class InboundMessage:
    provider: str
    destination: str
    message_id: str
    text: str
    sender_id: str | None = None
    send_address: str | None = None
    raw: dict[str, Any] | None = None
    # "p2p" (1:1 with the bot) or "group" (multi-user chat). Used by the
    # identity resolver to decide between auto-provision and OAuth prompt.
    chat_type: str = "group"
    # Feishu/Lark identifier preferences. The auth resolver tries
    # union_id first, then open_id.
    sender_open_id: str | None = None
    sender_union_id: str | None = None
    # If the provider includes the sender's verified email (rare on IM
    # webhooks, but possible on Slack-like providers), helps the
    # resolver link to an existing account.
    sender_email: str | None = None


class SessionSnapshot(BaseModel):
    id: str
    title: str | None = None
    status: str


class RunSnapshot(BaseModel):
    id: str | None = None
    status: str | None = None
    progress: int | None = None
    error_message: str | None = None


class EventStateSnapshot(BaseModel):
    callback_status: str | None = None
    current_step: str | None = None
    todos_total: int = 0
    todos_completed: int = 0


class MessageSnapshot(BaseModel):
    id: int
    role: str
    text: str
    text_preview: str | None = None


class UserInputRequestSnapshot(BaseModel):
    id: str
    tool_name: str
    tool_input: dict = Field(default_factory=dict)
    status: str
    expires_at: datetime
    answered_at: datetime | None = None


class ImBackendEvent(BaseModel):
    id: str
    type: str
    version: int = 1
    occurred_at: datetime
    user_id: str
    session: SessionSnapshot
    run: RunSnapshot | None = None
    state: EventStateSnapshot | None = None
    message: MessageSnapshot | None = None
    user_input_request: UserInputRequestSnapshot | None = None
