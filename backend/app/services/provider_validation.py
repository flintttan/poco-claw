"""Provider-name validation helpers for the IM integration.

Every code path that accepts a ``provider`` string from outside the
parse functions (``parse_feishu_update`` etc., which hardcode the
value) must validate against :data:`app.services.constants.KNOWN_IM_PROVIDERS`.
The Pydantic schemas (e.g. ``BindingCodeCreateRequest``) reject
unknown values at the API boundary, but services and repositories
that take a ``provider`` argument directly can be called from
internal code paths (e.g. ``IdentityResolver._auto_bind_from_oauth``
receives a provider from an OAuth callback) where there is no
upstream Pydantic check.

``assert_known_provider`` raises :class:`AppException` for unknown
values, which the global error handler converts to a 400 response.
It is intentionally cheap (one set lookup) and side-effect free so
it can be called at every service entrypoint without performance
concerns.
"""

from __future__ import annotations

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.constants import KNOWN_IM_PROVIDERS


def assert_known_provider(provider: str | None) -> str:
    """Validate ``provider`` is a known IM provider name.

    Args:
        provider: Candidate provider name. Empty / None is rejected
            because every code path that calls this helper expects a
            non-empty value.

    Returns:
        The lower-cased, stripped provider name (a defensive
        normalisation so callers do not have to repeat it).

    Raises:
        AppException: 400 INVALID_ARGUMENT if the provider is not
            in :data:`app.services.constants.KNOWN_IM_PROVIDERS`.
    """
    cleaned = (provider or "").strip().lower()
    if not cleaned:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="provider is required",
        )
    if cleaned not in KNOWN_IM_PROVIDERS:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=(
                f"unknown provider {cleaned!r}; "
                f"must be one of {sorted(KNOWN_IM_PROVIDERS)}"
            ),
        )
    return cleaned


__all__ = ["assert_known_provider"]
