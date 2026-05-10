from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ServerCreateRequest(BaseModel):
    name: str


class ServerOwnershipTransferRequest(BaseModel):
    new_owner_user_id: str


class ServerResponse(BaseModel):
    server_id: UUID = Field(validation_alias=AliasChoices("id", "server_id"))
    name: str
    slug: str
    kind: str
    owner_user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
