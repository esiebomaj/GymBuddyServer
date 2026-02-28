from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from app.auth import verify_token
from app.config import Settings, get_settings

security = HTTPBearer()


def get_supabase(settings: Annotated[Settings, Depends(get_settings)]) -> Client:
    """Supabase client using the service-role key for server-side operations."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Extract and verify the current user from the Authorization header."""
    return verify_token(credentials.credentials)


SupabaseDep = Annotated[Client, Depends(get_supabase)]
CurrentUserDep = Annotated[dict, Depends(get_current_user)]
