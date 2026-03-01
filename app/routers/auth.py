from fastapi import APIRouter

from app.dependencies import CurrentUserDep
from app.models.visit import MeResponse

router = APIRouter(tags=["auth"], prefix="/api/auth")


@router.get("/me")
async def get_me(user: CurrentUserDep):
    """Return the authenticated user's profile from the JWT payload."""
    meta = user.get("user_metadata", {})

    return MeResponse(
        id=user.get("sub"),
        email=user.get("email"),
        name=meta.get("name", meta.get("full_name", "")),
        photo_url=meta.get("photo_url", meta.get("avatar_url")),
    )
