"""UUID parsing helpers shared by service-layer code.

The codebase parses UUIDs in two flavours:

- :func:`try_parse_uuid` returns ``None`` on failure. Useful for
  read-only paths (callbacks, snapshot hydration) where a malformed
  identifier is data, not a user error.
- :func:`parse_uuid_or_error` raises :class:`AppException` with a
  400 status. Useful for command handlers (e.g. ``/server <uuid>``)
  where the user typed the value and a clear error message helps
  them fix it.

Both helpers accept ``str``, ``UUID``, or any value that has a
``__str__`` method (e.g. ``UUID``, integer via ``__str__``). All
non-stringifiable values are treated as a failure.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException


def try_parse_uuid(value: Any) -> uuid.UUID | None:
    """Best-effort UUID parse; returns ``None`` on failure.

    Args:
        value: Candidate value. ``None`` and unparseable values
            return ``None``. ``UUID`` instances are returned
            unchanged so the round-trip is lossless.

    Returns:
        The parsed :class:`uuid.UUID` or ``None`` if the value is
        missing / malformed.
    """
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def parse_uuid_or_error(value: Any, *, field: str = "id") -> uuid.UUID:
    """Strict UUID parse; raises :class:`AppException` on failure.

    Args:
        value: Candidate value.
        field: Human-readable field name for the error message
            (e.g. ``"server_id"`` for the ``/server`` command).

    Returns:
        The parsed :class:`uuid.UUID`.

    Raises:
        AppException: 400 BAD_REQUEST if the value is missing or
            malformed. The message includes the offending input
            (truncated to 64 chars to keep log lines manageable) so
            operators can identify typos.
    """
    parsed = try_parse_uuid(value)
    if parsed is None:
        # Truncate the value in the error message so a 1MB blob
        # does not blow up the response body.
        raw = "" if value is None else str(value)
        display = raw if len(raw) <= 64 else raw[:64] + "..."
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=(f"{field} must be a valid UUID; got {display!r}"),
        )
    return parsed


__all__ = ["try_parse_uuid", "parse_uuid_or_error"]
