from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, SupabaseDep
from app.models.settings import SettingsResponse, SettingsUpdate

router = APIRouter(tags=["settings"], prefix="/api/settings")


def _gym_day_started_this_week(gym_days: list[int], lock_start_time: str) -> bool:
    """True if any gym day's lock window has already started this Mon-Sun week.

    ``gym_days`` uses the JS convention: 0=Sun, 1=Mon … 6=Sat.
    """
    now = datetime.now()
    py_weekday = now.weekday()  # 0=Mon … 6=Sun

    start_h, start_m = (int(p) for p in lock_start_time.split(":"))

    for gd in gym_days:
        offset = (gd - 1) % 7  # convert to Mon-based: Mon=0 … Sun=6
        if offset < py_weekday:
            return True
        if offset == py_weekday:
            if now.hour > start_h or (now.hour == start_h and now.minute >= start_m):
                return True
    return False


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
        .select("gym_days, lock_start_time")
        .eq("user_id", uid)
        .maybe_single()
        .execute()
    )

    if current.data and _gym_day_started_this_week(
        current.data["gym_days"],
        str(current.data["lock_start_time"])[:5],
    ):
        raise HTTPException(
            status_code=423,
            detail="Schedule is locked for the current week. You can make changes next week.",
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
