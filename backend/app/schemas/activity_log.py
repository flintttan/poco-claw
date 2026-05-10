from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ActivityLogResponse(BaseModel):
    activity_log_id: UUID = Field(
        validation_alias=AliasChoices("id", "activity_log_id")
    )
    workspace_id: UUID
    actor_user_id: str | None
    action: str
    target_type: str
    target_id: str
    metadata: dict = Field(validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
