"""Helpers for building structured-log ``extra`` fields for the IM path.

The IM inbound and outbound paths log at several junctures (channel
disabled, server ACL fail, reply delivery failure, etc.). Without a
shared helper, every log site reinvents the field set and the result
is inconsistent: some include ``user_id``, some do not, almost
none include the IM-side identifiers (``sender_open_id`` /
``sender_union_id``) that operators need to find the conversation
in the IM provider's admin console.

:func:`inbound_message_log_context` and :func:`event_log_context`
return a dict that can be unpacked into ``logger.<level>(extra=...)``.
Both are pure and side-effect free so they can be called from hot
paths without performance concerns.

The helpers intentionally do **not** log the message text — the
agent's responses are already persisted elsewhere and including the
text here would (a) duplicate PII in the log pipeline and (b) make
the structured-log schema inconsistent across log lines.
"""

from __future__ import annotations

from typing import Any

from app.schemas.im import ImBackendEvent, InboundMessage


def inbound_message_log_context(
    message: InboundMessage,
    *,
    user_id: str | None = None,
    channel_id: int | None = None,
    **extras: Any,
) -> dict[str, Any]:
    """Build a structured-log ``extra`` dict for an inbound message.

    Args:
        message: The :class:`InboundMessage` that triggered the log.
        user_id: The Poco user id (resolved by
            :class:`IdentityResolver`), if known. May be ``None``
            when the resolver has not yet run.
        channel_id: The IM channel id, if known.
        **extras: Additional fields to merge into the result. Use
            for the specific context of one log site (``reason``,
            ``attempt_count``, etc.) so the helper does not need to
            grow a long parameter list.

    Returns:
        A new dict that callers can pass straight to
        ``logger.<level>(extra=...)``.
    """
    base: dict[str, Any] = {
        "provider": message.provider,
        "destination": message.destination,
        "message_id": message.message_id,
        "chat_type": message.chat_type,
    }
    if message.sender_open_id:
        base["sender_open_id"] = message.sender_open_id
    if message.sender_union_id:
        base["sender_union_id"] = message.sender_union_id
    if user_id:
        base["user_id"] = user_id
    if channel_id is not None:
        base["channel_id"] = channel_id
    base.update(extras)
    return base


def event_log_context(
    event: ImBackendEvent,
    **extras: Any,
) -> dict[str, Any]:
    """Build a structured-log ``extra`` dict for an outbound event.

    Args:
        event: The :class:`ImBackendEvent` being processed.
        **extras: Additional fields to merge into the result.

    Returns:
        A new dict suitable for ``logger.<level>(extra=...)``.
    """
    base: dict[str, Any] = {
        "event_type": event.type,
        "event_id": event.id,
        "session_id": event.session.id,
        "user_id": event.user_id,
    }
    base.update(extras)
    return base


__all__ = [
    "inbound_message_log_context",
    "event_log_context",
]
