import base64
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an image classifier for a gym-tracking app. "
    "The user claims to have done a specific workout and submitted a photo as proof. "
    "Determine whether the photo shows a legitimate workout or gym-related activity. "
    "This includes: being at a gym, using exercise equipment, doing bodyweight exercises, "
    "running outdoors, stretching, yoga, swimming, cycling, boxing, or any other recognizable "
    "form of physical exercise. A selfie at the gym or a photo of gym equipment also counts.\n\n"
    "Also consider whether the photo is consistent with the claimed workout type. "
    "For example, a photo of a swimming pool would not match a claimed workout type of 'weights'."
)


class WorkoutImageValidation(BaseModel):
    is_workout: bool
    matches_workout_type: bool
    reason: str


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def validate_workout_image(
    image_bytes: bytes,
    content_type: str,
    workout_type: str,
) -> WorkoutImageValidation:
    """Ask GPT-4o-mini to classify whether the image depicts a workout
    consistent with the claimed workout type.

    Raises on API errors so the caller can decide how to handle them.
    """
    b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:{content_type};base64,{b64}"

    client = _get_client()
    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri, "detail": "low"},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"The user claims this is a '{workout_type}' workout. "
                            "Is this a legitimate workout photo, and does it match the claimed type?"
                        ),
                    },
                ],
            },
        ],
        response_format=WorkoutImageValidation,
        max_tokens=150,
        temperature=0,
    )

    return response.choices[0].message.parsed
