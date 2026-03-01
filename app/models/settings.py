from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    weekly_goal: int
    gym_days: list[int]
    lock_start_time: str
    lock_end_time: str


class SettingsUpdate(BaseModel):
    weekly_goal: int | None = Field(default=None, ge=1, le=7)
    gym_days: list[int] | None = None
    lock_start_time: str | None = None
    lock_end_time: str | None = None
