from fastapi import APIRouter

from app.dependencies import CurrentUserDep

router = APIRouter(tags=["auth"], prefix="/api/auth")


@router.get("/me")
async def get_me(user: CurrentUserDep):
    """Return the authenticated user's profile from the JWT payload."""
    return {
        "id": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
    }
