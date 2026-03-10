from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, SupabaseDep
from app.models.settings import SettingsResponse, SettingsUpdate

router = APIRouter(tags=["settings"], prefix="/api/settings")


def _in_lock_window(gym_days: list[int], lock_start: str, lock_end: str) -> bool:
    """True if right now is inside a lock window (gym day + within start/end time).

    ``gym_days`` uses the JS convention: 0=Sun, 1=Mon … 6=Sat.
    """
    now = datetime.now()
    if now.weekday() == 6:
        js_day = 0  # Sunday
    else:
        js_day = now.weekday() + 1

    if js_day not in gym_days:
        return False

    start_h, start_m = (int(p) for p in lock_start.split(":"))
    end_h, end_m = (int(p) for p in lock_end.split(":"))
    current = now.hour * 60 + now.minute
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m

    return current >= start and current <= end


@router.get("", response_model=SettingsResponse)
async def get_settings(user: CurrentUserDep, db: SupabaseDep):
    """Return the authenticated user's gym schedule and lock preferences."""
    uid = user["sub"]
    result = (
        db.table("user_settings")
        .select("weekly_goal, gym_days, lock_start_time, lock_end_time")
        .eq("user_id", uid)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found — the signup trigger may not have fired.",
        )

    row = result.data
    return SettingsResponse(
        weekly_goal=row["weekly_goal"],
        gym_days=row["gym_days"],
        lock_start_time=str(row["lock_start_time"])[:5],
        lock_end_time=str(row["lock_end_time"])[:5],
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    user: CurrentUserDep,
    db: SupabaseDep,
):
    """Update the authenticated user's gym schedule and lock preferences."""
    uid = user["sub"]

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    current = (
        db.table("user_settings")
        .select("gym_days, lock_start_time, lock_end_time")
        .eq("user_id", uid)
        .maybe_single()
        .execute()
    )

    if current.data and _in_lock_window(
        current.data["gym_days"],
        str(current.data["lock_start_time"])[:5],
        str(current.data["lock_end_time"])[:5],
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        visit = (
            db.table("visits")
            .select("id")
            .eq("user_id", uid)
            .eq("visit_date", today)
            .maybe_single()
            .execute()
        )
        if not visit.data:
            raise HTTPException(
                status_code=423,
                detail="Cannot change schedule while apps are locked. Submit gym proof first.",
            )

    result = (
        db.table("user_settings")
        .update({**updates, "updated_at": "now()"})
        .eq("user_id", uid)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found.",
        )

    row = result.data[0]
    return SettingsResponse(
        weekly_goal=row["weekly_goal"],
        gym_days=row["gym_days"],
        lock_start_time=str(row["lock_start_time"])[:5],
        lock_end_time=str(row["lock_end_time"])[:5],
    )
