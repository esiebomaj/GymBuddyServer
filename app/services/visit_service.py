import uuid
from datetime import date, timedelta

from fastapi import HTTPException, UploadFile, status
from supabase import Client


ALLOWED_WORKOUT_TYPES = {
    "weights", "cardio", "yoga", "boxing",
    "cycling", "swimming", "hiit", "other",
}

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


def _sunday_of(d: date) -> date:
    """Return the Sunday of the week containing *d* (week starts Sunday)."""
    # Python weekday(): Mon=0 .. Sun=6; days since Sunday = (weekday() + 1) % 7
    return d - timedelta(days=(d.weekday() + 1) % 7)


async def upload_proof_photo(
    db: Client,
    user_id: str,
    file: UploadFile,
) -> str:
    """Upload a proof photo to Supabase Storage and return its public URL."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {file.content_type}",
        )

    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
    path = f"{user_id}/{date.today().isoformat()}_{uuid.uuid4().hex[:8]}.{ext}"

    contents = await file.read()
    db.storage.from_("proof-photos").upload(
        path,
        contents,
        {"content-type": file.content_type},
    )

    return db.storage.from_("proof-photos").get_public_url(path)


def create_visit(
    db: Client,
    user_id: str,
    visit_date: date,
    workout_type: str,
    note: str | None,
    photo_url: str | None,
) -> dict:
    """Insert a gym_visits row. Raises 409 if already visited today."""
    if workout_type not in ALLOWED_WORKOUT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workout_type: {workout_type}",
        )

    result = (
        db.table("gym_visits")
        .insert({
            "user_id": user_id,
            "visit_date": visit_date.isoformat(),
            "workout_type": workout_type,
            "note": note,
            "photo_url": photo_url,
        })
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already logged a visit for today.",
        )

    return result.data[0]


def update_streak_if_needed(db: Client, user_id: str, weekly_goal: int) -> dict:
    """Check if the weekly goal was just met and bump the streak accordingly."""
    today = date.today()
    week_start = _sunday_of(today)
    week_end = week_start + timedelta(days=6)

    visits_this_week = (
        db.table("gym_visits")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("visit_date", week_start.isoformat())
        .lte("visit_date", week_end.isoformat())
        .execute()
    )
    weekly_count = visits_this_week.count or 0

    streak_row = (
        db.table("streaks")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    ).data

    current = streak_row["current_streak"]
    longest = streak_row["longest_streak"]
    last_week = streak_row["last_completed_week"]

    if weekly_count >= weekly_goal and (last_week is None or last_week != week_start.isoformat()):
        current += 1
        longest = max(longest, current)
        db.table("streaks").update({
            "current_streak": current,
            "longest_streak": longest,
            "last_completed_week": week_start.isoformat(),
            "updated_at": "now()",
        }).eq("user_id", user_id).execute()

    return {
        "current_streak": current,
        "longest_streak": longest,
        "last_completed_week": last_week,
    }


def get_stats(db: Client, user_id: str) -> dict:
    """Build the combined stats payload for GET /api/stats."""
    today = date.today()
    week_start = _sunday_of(today)
    week_end = week_start + timedelta(days=6)

    # Weekly visits
    weekly_result = (
        db.table("gym_visits")
        .select("visit_date")
        .eq("user_id", user_id)
        .gte("visit_date", week_start.isoformat())
        .lte("visit_date", week_end.isoformat())
        .order("visit_date")
        .execute()
    )
    visit_dates = [r["visit_date"] for r in (weekly_result.data or [])]
    visited_today = today.isoformat() in visit_dates

    # User settings (needed for gym_days matching and weekly_goal)
    settings_row = (
        db.table("user_settings")
        .select("weekly_goal, gym_days")
        .eq("user_id", user_id)
        .single()
        .execute()
    ).data

    gym_days = settings_row.get("gym_days", [])  # 0=Sun, 1=Mon … 6=Sat
    scheduled_iso = {
        (week_start + timedelta(days=d)).isoformat()
        for d in gym_days
    }
    matching_visit_dates = [d for d in visit_dates if d in scheduled_iso]

    # Total visits
    total_result = (
        db.table("gym_visits")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    total_visits = total_result.count or 0

    # Streak
    streak_row = (
        db.table("streaks")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    ).data

    current_streak = streak_row["current_streak"]
    longest_streak = streak_row["longest_streak"]
    last_completed = streak_row["last_completed_week"]

    # Reset streak if the user did not achieve their weekly target in any week
    # since the last completed week (i.e. there is a gap of at least one full week).
    if last_completed:
        last_completed_week_start = date.fromisoformat(last_completed)
        if week_start - last_completed_week_start > timedelta(days=7):
            current_streak = 0
            db.table("streaks").update({
                "current_streak": 0,
                "updated_at": "now()",
            }).eq("user_id", user_id).execute()

    return {
        "weekly_visits": len(visit_dates),
        "matching_weekly_visits": len(matching_visit_dates),
        "weekly_goal": settings_row["weekly_goal"],
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_visits": total_visits,
        "visited_today": visited_today,
        "visit_dates_this_week": visit_dates,
        "matching_visit_dates_this_week": matching_visit_dates,
    }
