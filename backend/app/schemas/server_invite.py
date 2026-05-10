from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.server_member import ServerRole


class ServerInviteCreateRequest(BaseModel):
    role: ServerRole = Field(default="member")
    expires_in_days: int = Field(default=7, ge=1, le=30)
    max_uses: int = Field(default=1, ge=1, le=100)


class ServerInviteAcceptRequest(BaseModel):
    token: str


class ServerInviteRevokeRequest(BaseModel):
    pass


class ServerInviteResponse(BaseModel):
    invite_id: UUID = Field(validation_alias=AliasChoices("id", "invite_id"))
    server_id: UUID
    token: str
    role: ServerRole
    expires_at: datetime
    created_by: str
    max_uses: int
    used_count: int
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
