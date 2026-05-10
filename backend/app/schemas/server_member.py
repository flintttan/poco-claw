from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.user_profile import UserPublicProfileResponse

ServerRole = Literal["owner", "admin", "member"]


class ServerMemberRoleUpdateRequest(BaseModel):
    role: ServerRole


class ServerMemberResponse(BaseModel):
    membership_id: int = Field(validation_alias=AliasChoices("id", "membership_id"))
    server_id: UUID
    user_id: str
    user: UserPublicProfileResponse | None = None
    role: ServerRole
    joined_at: datetime
    invited_by: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
