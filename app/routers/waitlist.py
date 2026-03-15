import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["waitlist"], prefix="/api")


class WaitlistRequest(BaseModel):
    email: EmailStr


@router.post("/waitlist", status_code=status.HTTP_204_NO_CONTENT)
async def join_waitlist(body: WaitlistRequest):
    """Add email to Mailchimp waitlist."""
    settings = get_settings()
    dc = settings.mailchimp_dc
    url = f"https://{dc}.api.mailchimp.com/3.0/lists/{settings.mailchimp_list_id}/members"

    status_code, data = await _send_to_mailchimp(
        url=url,
        api_key=settings.mailchimp_api_key,
        email=body.email,
    )
    print(status_code, data)

    if status_code == 400:
        # Already subscribed is idempotent success
        if data.get("title") == "Member Exists" or "already a list member" in str(data.get("detail", "")).lower():
            return None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=data.get("detail", data.get("title", "Invalid request")))

    if status_code >= 400:
        logger.warning("Mailchimp error %s: %s", status_code, data)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to add to waitlist. Please try again.",
        )

    return None


async def _send_to_mailchimp(*, url: str, api_key: str, email: str) -> tuple[int, dict]:
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "email_address": email,
                "status": "subscribed",
            },
            timeout=10.0,
        )
    data = resp.json() if resp.content else {}
    return resp.status_code, data
