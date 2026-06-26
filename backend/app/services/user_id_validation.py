"""User-id length validation helper.

``User.id`` and the audit columns that reference it
(``Channel.last_bound_by_user_id`` etc.) are all ``String(255)``.
If an oversized value is ever assigned, PostgreSQL raises a
``value too long`` error from the implicit cast on ``db.flush()``,
which is opaque to debug. This helper centralises the length check
so we can raise a clear :class:`AppException` instead.

The 255-character limit is shared with the database column
definition; see ``backend/app/models/user.py`` and
``backend/app/models/im.py``. Keep these in sync — if the column
is widened, widen the constant here.
"""

from __future__ import annotations

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException

# Maximum length of a Poco ``user_id`` value. Matches the ``String(255)``
# column width on ``users.id`` and any audit column that references it
# (e.g. ``channels.last_bound_by_user_id``).
MAX_USER_ID_LENGTH = 255


def assert_valid_user_id(user_id: str | None) -> str:
    """Validate ``user_id`` fits in the database column.

    Args:
        user_id: Candidate user identifier. ``None`` / empty is
            rejected because every call site already requires a
            non-empty value before calling this helper.

    Returns:
        The input string, unchanged, so callers can chain
            ``channel.last_bound_by_user_id = assert_valid_user_id(uid)``.

    Raises:
        AppException: 400 BAD_REQUEST if the value is empty or
            longer than :data:`MAX_USER_ID_LENGTH`.
    """
    if user_id is None:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="user_id is required",
        )
    cleaned = user_id.strip() if user_id else ""
    if not cleaned:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="user_id is required",
        )
    if len(cleaned) > MAX_USER_ID_LENGTH:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=(
                f"user_id too long ({len(cleaned)} chars); "
                f"maximum is {MAX_USER_ID_LENGTH}"
            ),
        )
    return cleaned


__all__ = ["assert_valid_user_id", "MAX_USER_ID_LENGTH"]
