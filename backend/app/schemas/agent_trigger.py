from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


TriggerType = Literal["channel_mention", "agent_dm", "agent_collaboration"]
TriggerActorType = Literal["user", "agent", "system"]


class TriggerSourceActor(BaseModel):
    """Actor that caused a persistent agent trigger."""

    actor_type: TriggerActorType
    user_id: str | None = None
    agent_identity_id: UUID | None = None
    display_name: str | None = None


class TriggerReferences(BaseModel):
    """Channel objects referenced by a trigger."""

    message_ids: list[UUID] = Field(default_factory=list)
    artifact_ids: list[UUID] = Field(default_factory=list)
    task_ids: list[UUID] = Field(default_factory=list)


class TriggerHandoff(BaseModel):
    """Handoff metadata used for dedupe and loop control."""

    parent_run_id: UUID | None = None
    depth: int = Field(default=0, ge=0)
    dedupe_key: str | None = None


class AgentTriggerEnvelope(BaseModel):
    """Structured channel trigger context persisted alongside a run."""

    version: Literal[1] = 1
    trigger_type: TriggerType
    server_id: UUID
    channel_id: UUID
    trigger_message_id: UUID
    thread_root_message_id: UUID | None = None
    target_agent_identity_id: UUID
    target_agent_handle: str
    source_actor: TriggerSourceActor
    references: TriggerReferences = Field(default_factory=TriggerReferences)
    handoff: TriggerHandoff = Field(default_factory=TriggerHandoff)
