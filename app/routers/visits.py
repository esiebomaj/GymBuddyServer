import logging
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.dependencies import CurrentUserDep, SupabaseDep
from app.models.visit import StatsResponse, VisitResponse
from app.services.image_validation import validate_workout_image
from app.services.visit_service import (
    create_visit,
    get_stats,
    update_streak_if_needed,
    upload_proof_photo,
)

logger = logging.getLogger(__name__)

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

    Validates the photo with an LLM vision model to confirm it depicts a
    workout, uploads it to Supabase Storage, inserts a gym_visits row,
    and updates the streak if the weekly goal is now met.
    """
    uid = user["sub"]
    today = date.today()

    photo_url = None
    if photo:
        image_bytes = await photo.read()

        try:
            result = await validate_workout_image(image_bytes, photo.content_type, workout_type)
        except Exception:
            logger.error("Could not validate photo as a workout image", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not validate photo as a workout image",
            )
        if result and not result.is_workout:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Photo does not appear to be a workout image: {result.reason}",
            )
        if result and not result.matches_workout_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Photo does not match claimed workout type '{workout_type}': {result.reason}",
            )

        await photo.seek(0)
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
