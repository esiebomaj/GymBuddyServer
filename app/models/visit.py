from pydantic import BaseModel

from app.models.settings import SettingsResponse


class VisitResponse(BaseModel):
    id: str
    visit_date: str
    workout_type: str
    note: str | None = None
    photo_url: str | None = None
    created_at: str


class StatsResponse(BaseModel):
    weekly_visits: int
    matching_weekly_visits: int
    weekly_goal: int
    current_streak: int
    longest_streak: int
    total_visits: int
    visited_today: bool
    visit_dates_this_week: list[str]
    matching_visit_dates_this_week: list[str]


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    photo_url: str | None = None