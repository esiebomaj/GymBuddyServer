from datetime import date

from fastapi import APIRouter, File, Form, UploadFile

from app.dependencies import CurrentUserDep, SupabaseDep
from app.models.visit import StatsResponse, VisitResponse
from app.services.visit_service import (
    create_visit,
    get_stats,
    update_streak_if_needed,
    upload_proof_photo,
)

router = APIRouter(tags=["visits"], prefix="/api")


@router.post("/visits", response_model=VisitResponse, status_code=201)
async def submit_visit(
    user: CurrentUserDep,
    db: SupabaseDep,
    workout_type: str = Form(...),
    note: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
):
    """Submit gym proof: photo + workout type + optional note.

    Uploads the photo to Supabase Storage, inserts a gym_visits row,
    and updates the streak if the weekly goal is now met.
    """
    uid = user["sub"]
    today = date.today()

    photo_url = None
    if photo:
        photo_url = await upload_proof_photo(db, uid, photo)

    visit = create_visit(db, uid, today, workout_type, note, photo_url)

    settings = (
        db.table("user_settings")
        .select("weekly_goal")
        .eq("user_id", uid)
        .single()
        .execute()
    ).data
    update_streak_if_needed(db, uid, settings["weekly_goal"])

    return VisitResponse(
        id=visit["id"],
        visit_date=visit["visit_date"],
        workout_type=visit["workout_type"],
        note=visit.get("note"),
        photo_url=visit.get("photo_url"),
        created_at=visit["created_at"],
    )


@router.get("/stats", response_model=StatsResponse)
async def get_user_stats(user: CurrentUserDep, db: SupabaseDep):
    """Combined stats: weekly visits, streak, total visits, visited_today."""
    stats = get_stats(db, user["sub"])
    print(f"Stats: {stats}")
    return stats
