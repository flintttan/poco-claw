from pydantic import BaseModel, Field


class RunNotifyRequest(BaseModel):
    run_id: str = Field(min_length=1)
    schedule_mode: str = Field(default="immediate", min_length=1)
    session_id: str | None = None
