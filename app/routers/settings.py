from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, SupabaseDep
from app.models.settings import SettingsResponse, SettingsUpdate

router = APIRouter(tags=["settings"], prefix="/api/settings")


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
        lock_start_time=str(row["lock_start_time"]),
        lock_end_time=str(row["lock_end_time"]),
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
        lock_start_time=str(row["lock_start_time"]),
        lock_end_time=str(row["lock_end_time"]),
    )
