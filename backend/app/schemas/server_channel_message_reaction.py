from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.user_profile import UserPublicProfileResponse

ServerChannelMessageReactionActorType = Literal["user", "agent"]


class ServerChannelMessageReactionRequest(BaseModel):
    emoji: str = Field(min_length=1, max_length=64)


class ServerChannelMessageReactionActorResponse(BaseModel):
    actor_type: ServerChannelMessageReactionActorType
    user_id: str | None = None
    user: UserPublicProfileResponse | None = None
    agent_identity_id: UUID | None = None
    agent_handle: str | None = None
    agent_label: str | None = None


class ServerChannelMessageReactionGroupResponse(BaseModel):
    emoji: str
    count: int
    reacted_by_current_user: bool = False
    reacted_by_current_agent: bool = False
    actors: list[ServerChannelMessageReactionActorResponse] = Field(
        default_factory=list
    )


class ServerChannelMessageReactionOperationResponse(BaseModel):
    action: str
    message_id: UUID
    reaction: ServerChannelMessageReactionGroupResponse | None = None


class AgentChannelMessageReactionRequest(BaseModel):
    message_id: UUID
    emoji: str = Field(min_length=1, max_length=64)
