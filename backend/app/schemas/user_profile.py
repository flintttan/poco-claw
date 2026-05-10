from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class UserPublicProfileResponse(BaseModel):
    user_id: str = Field(validation_alias=AliasChoices("id", "user_id"))
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
