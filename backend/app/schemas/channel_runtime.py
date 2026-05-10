from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.server_channel_message import ServerChannelMessageResponse


class AgentChannelRuntimeScope(BaseModel):
    session_id: UUID
    user_id: str
    server_id: UUID
    channel_id: UUID
    agent_identity_id: UUID
    agent_handle: str
    agent_label: str
    agent_preset_id: int
    trigger_message_id: UUID | None = None
    thread_root_message_id: UUID | None = None
    parent_run_id: UUID | None = None
    handoff_depth: int = 0
    trigger_context: dict[str, Any] = Field(default_factory=dict)


class AgentChannelMessageReadRequest(BaseModel):
    message_ids: list[UUID] = Field(default_factory=list)
    thread_root_message_id: UUID | None = None
    anchor_message_id: UUID | None = None
    direction: Literal["before", "after"] | None = None
    include_anchor: bool = True
    read_all: bool = False
    limit: int | None = None


class AgentChannelMessagesReadResponse(BaseModel):
    messages: list[ServerChannelMessageResponse]


class AgentChannelAgentResponse(BaseModel):
    agent_identity_id: UUID
    handle: str
    display_name: str
    description: str | None = None
    visual_key: str | None = None


class AgentChannelAgentsListResponse(BaseModel):
    agents: list[AgentChannelAgentResponse]


class AgentChannelCollaborationRequest(BaseModel):
    agent_handle: str
    request_text: str
    reason: str | None = None
    mode: Literal["consult", "handoff"] = "consult"
    thread_root_message_id: UUID | None = None
    reference_message_ids: list[UUID] = Field(default_factory=list)
    reference_artifact_ids: list[UUID] = Field(default_factory=list)


class AgentChannelCollaborationResponse(BaseModel):
    action: Literal["request_agent_collaboration"] = "request_agent_collaboration"
    status: str
    target_agent_identity_id: UUID
    target_agent_handle: str
    session_id: UUID
    run_id: UUID | None = None
    queue_item_id: UUID | None = None
    dedupe_key: str
