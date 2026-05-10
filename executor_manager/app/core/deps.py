from fastapi import Header, HTTPException

from app.core.settings import get_settings


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """Validate internal service-to-service requests."""
    token = (x_internal_token or "").strip()
    settings = get_settings()
    if not token or token != settings.internal_api_token:
        raise HTTPException(status_code=403, detail="Invalid internal token")


def require_callback_token(
    authorization: str | None = Header(default=None),
) -> None:
    """Validate the callback token sent by executor-side helper scripts."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    settings = get_settings()
    if not token or token != settings.callback_token:
        raise HTTPException(status_code=403, detail="Invalid callback token")
