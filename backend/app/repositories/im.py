import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.im import (
    ActiveSession,
    Channel,
    ChannelDelivery,
    ChannelMember,
    DedupEvent,
    ImBinding,
    ImBindingCode,
    ImEventOutbox,
    WatchedSession,
)


class ActiveSessionRepository:
    @staticmethod
    def get_by_channel(db: Session, *, channel_id: int) -> ActiveSession | None:
        stmt = select(ActiveSession).where(ActiveSession.channel_id == channel_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def create(db: Session, *, channel_id: int, session_id: str) -> ActiveSession:
        entry = ActiveSession(channel_id=channel_id, session_id=session_id)
        db.add(entry)
        return entry

    @staticmethod
    def delete(db: Session, entry: ActiveSession) -> None:
        db.delete(entry)

    @staticmethod
    def list_by_session(db: Session, *, session_id: str) -> list[ActiveSession]:
        stmt = select(ActiveSession).where(ActiveSession.session_id == session_id)
        return list(db.execute(stmt).scalars().all())


class ChannelRepository:
    """Channel access layer (previously inline in service module)."""

    @staticmethod
    def get_by_provider_destination(
        db: Session, *, provider: str, destination: str
    ) -> Channel | None:
        stmt = select(Channel).where(
            Channel.provider == provider,
            Channel.destination == destination,
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_by_id(db: Session, channel_id: int) -> Channel | None:
        return db.get(Channel, channel_id)

    @staticmethod
    def list_enabled(db: Session) -> list[Channel]:
        stmt = select(Channel).where(Channel.enabled.is_(True))
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_by_ids(
        db: Session, channel_ids: list[int] | set[int] | tuple[int, ...]
    ) -> list[Channel]:
        """Batch fetch channels by primary key.

        Avoids the N+1 pattern in :func:`BackendEventService._get_target_channel_ids`
        where every candidate ``channel_id`` was loaded individually.
        An empty input returns an empty list without hitting the database.
        """
        if not channel_ids:
            return []
        stmt = select(Channel).where(Channel.id.in_(channel_ids))
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def create(
        db: Session,
        *,
        provider: str,
        destination: str,
        owner_user_id: str,
        chat_type: str = "group",
    ) -> Channel:
        channel = Channel(
            provider=provider,
            destination=destination,
            owner_user_id=owner_user_id,
            chat_type=chat_type,
        )
        db.add(channel)
        return channel

    @staticmethod
    def set_subscribe_all(db: Session, *, channel_id: int, enabled: bool) -> Channel:
        channel = db.get(Channel, channel_id)
        if not channel:
            raise ValueError(f"Channel not found: {channel_id}")
        channel.subscribe_all = bool(enabled)
        return channel

    @staticmethod
    def list_by_server(
        db: Session,
        *,
        server_id: uuid.UUID,
    ) -> list[Channel]:
        """Return all channels bound to ``server_id``.

        Used by the server-detail UI to surface "which IM chats are
        currently linked to this server". The list is not filtered
        by ``enabled`` — the UI may want to show disabled channels
        so the user can re-enable them. Order by id so the list is
        stable across calls (avoids a UI that randomly shuffles
        rows on every refresh).
        """
        stmt = (
            select(Channel)
            .where(Channel.server_id == server_id)
            .order_by(Channel.id.asc())
        )
        return list(db.execute(stmt).scalars().all())


class ChannelDeliveryRepository:
    @staticmethod
    def get_by_channel(db: Session, *, channel_id: int) -> ChannelDelivery | None:
        stmt = select(ChannelDelivery).where(ChannelDelivery.channel_id == channel_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_send_address(db: Session, *, channel_id: int) -> str | None:
        row = ChannelDeliveryRepository.get_by_channel(db, channel_id=channel_id)
        if not row:
            return None
        return row.send_address

    @staticmethod
    def create(
        db: Session,
        *,
        channel_id: int,
        send_address: str,
    ) -> ChannelDelivery:
        row = ChannelDelivery(channel_id=channel_id, send_address=send_address)
        db.add(row)
        return row


class DedupRepository:
    @staticmethod
    def exists(db: Session, *, key: str) -> bool:
        stmt = select(DedupEvent.key).where(DedupEvent.key == key)
        return db.execute(stmt).first() is not None

    @staticmethod
    def create(db: Session, *, key: str) -> DedupEvent:
        row = DedupEvent(key=key)
        db.add(row)
        return row


class WatchRepository:
    @staticmethod
    def create(db: Session, *, channel_id: int, session_id: str) -> WatchedSession:
        entry = WatchedSession(channel_id=channel_id, session_id=session_id)
        db.add(entry)
        return entry

    @staticmethod
    def delete(db: Session, entry: WatchedSession) -> None:
        db.delete(entry)

    @staticmethod
    def get_watch(
        db: Session,
        *,
        channel_id: int,
        session_id: str,
    ) -> WatchedSession | None:
        stmt = (
            select(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .where(WatchedSession.session_id == session_id)
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def list_by_session(db: Session, *, session_id: str) -> list[WatchedSession]:
        stmt = select(WatchedSession).where(WatchedSession.session_id == session_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_by_channel(db: Session, *, channel_id: int) -> list[WatchedSession]:
        stmt = (
            select(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .order_by(WatchedSession.created_at.desc(), WatchedSession.id.desc())
        )
        return list(db.execute(stmt).scalars().all())


class ImEventOutboxRepository:
    @staticmethod
    def _normalize_id(event_id: uuid.UUID | str) -> uuid.UUID:
        if isinstance(event_id, uuid.UUID):
            return event_id
        return uuid.UUID(str(event_id))

    @staticmethod
    def create_if_absent(
        db: Session,
        *,
        event_key: str,
        event_type: str,
        event_version: int,
        user_id: str,
        session_id: uuid.UUID | None,
        run_id: uuid.UUID | None,
        message_id: int | None,
        user_input_request_id: uuid.UUID | None,
        payload: dict[str, Any],
    ) -> ImEventOutbox:
        existing = ImEventOutboxRepository.get_by_event_key(db, event_key=event_key)
        if existing:
            return existing

        row = ImEventOutbox(
            event_key=event_key,
            event_type=event_type,
            event_version=event_version,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            message_id=message_id,
            user_input_request_id=user_input_request_id,
            payload=payload,
        )
        db.add(row)
        try:
            with db.begin_nested():
                db.flush([row])
        except IntegrityError:
            existing = ImEventOutboxRepository.get_by_event_key(db, event_key=event_key)
            if existing:
                return existing
            raise
        return row

    @staticmethod
    def get_by_event_key(db: Session, *, event_key: str) -> ImEventOutbox | None:
        stmt = select(ImEventOutbox).where(ImEventOutbox.event_key == event_key)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def claim_due_batch(
        db: Session,
        *,
        limit: int,
        lease_seconds: int,
    ) -> list[ImEventOutbox]:
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=max(5, lease_seconds))
        stmt = (
            select(ImEventOutbox)
            .where(ImEventOutbox.status != "delivered")
            .where(ImEventOutbox.next_attempt_at <= now)
            .where(
                or_(
                    ImEventOutbox.lease_expires_at.is_(None),
                    ImEventOutbox.lease_expires_at < now,
                )
            )
            .order_by(ImEventOutbox.created_at.asc(), ImEventOutbox.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        rows = list(db.execute(stmt).scalars().all())
        if not rows:
            return []

        for row in rows:
            row.status = "sending"
            row.attempt_count = int(row.attempt_count or 0) + 1
            row.lease_expires_at = lease_until
        return rows

    @staticmethod
    def mark_delivered(db: Session, *, event_id: uuid.UUID | str) -> None:
        row = db.get(ImEventOutbox, ImEventOutboxRepository._normalize_id(event_id))
        if row is None:
            return
        row.status = "delivered"
        row.delivered_at = datetime.now(timezone.utc)
        row.lease_expires_at = None
        row.last_error = None

    @staticmethod
    def mark_retry(
        db: Session,
        *,
        event_id: uuid.UUID | str,
        error_message: str,
        delay_seconds: float,
    ) -> None:
        row = db.get(ImEventOutbox, ImEventOutboxRepository._normalize_id(event_id))
        if row is None:
            return
        row.status = "pending"
        row.lease_expires_at = None
        row.last_error = error_message[:4000]
        row.next_attempt_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(0.5, delay_seconds)
        )


class ChannelMemberRepository:
    @staticmethod
    def get_by_channel_and_user(
        db: Session, *, channel_id: int, user_id: str
    ) -> ChannelMember | None:
        stmt = select(ChannelMember).where(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == user_id,
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def list_active_by_channel(db: Session, *, channel_id: int) -> list[ChannelMember]:
        stmt = (
            select(ChannelMember)
            .where(
                ChannelMember.channel_id == channel_id,
                ChannelMember.status == "active",
            )
            .order_by(ChannelMember.joined_at.asc(), ChannelMember.id.asc())
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_channels_for_user(db: Session, *, user_id: str) -> list[ChannelMember]:
        stmt = select(ChannelMember).where(
            ChannelMember.user_id == user_id,
            ChannelMember.status == "active",
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def create(
        db: Session,
        *,
        channel_id: int,
        user_id: str,
        role: str = "member",
    ) -> ChannelMember:
        entry = ChannelMember(channel_id=channel_id, user_id=user_id, role=role)
        db.add(entry)
        return entry


class ImBindingRepository:
    """Data access layer for ``im_bindings``.

    The resolver relies on the unique index ``(provider, im_user_id)``
    for the primary lookup. A secondary index on
    ``(provider, im_union_id)`` covers IM events that carry the union
    identifier but not the open/staff id (e.g. when the union id is the
    one forwarded by the bot while the open id is masked).
    """

    @staticmethod
    def get_by_provider_im_user_id(
        db: Session, *, provider: str, im_user_id: str
    ) -> ImBinding | None:
        if not provider or not im_user_id:
            return None
        stmt = select(ImBinding).where(
            ImBinding.provider == provider,
            ImBinding.im_user_id == im_user_id,
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_by_provider_im_union_id(
        db: Session, *, provider: str, im_union_id: str
    ) -> ImBinding | None:
        if not provider or not im_union_id:
            return None
        stmt = select(ImBinding).where(
            ImBinding.provider == provider,
            ImBinding.im_union_id == im_union_id,
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def list_for_user(db: Session, *, user_id: str) -> list[ImBinding]:
        stmt = (
            select(ImBinding)
            .where(ImBinding.user_id == user_id)
            .order_by(ImBinding.bound_at.desc(), ImBinding.id.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_by_id(db: Session, binding_id: int) -> ImBinding | None:
        return db.get(ImBinding, binding_id)

    @staticmethod
    def create(
        db: Session,
        *,
        user_id: str,
        provider: str,
        im_user_id: str,
        im_union_id: str | None = None,
        im_display_name: str | None = None,
        bound_via: str = "code",
    ) -> ImBinding:
        binding = ImBinding(
            user_id=user_id,
            provider=provider,
            im_user_id=im_user_id,
            im_union_id=im_union_id,
            im_display_name=im_display_name,
            bound_via=bound_via,
        )
        db.add(binding)
        return binding

    @staticmethod
    def delete(db: Session, binding: ImBinding) -> None:
        db.delete(binding)

    @staticmethod
    def touch_last_seen(db: Session, binding: ImBinding) -> None:
        binding.last_seen_at = datetime.now(timezone.utc)


class ImBindingCodeRepository:
    """Data access layer for ``im_binding_codes``.

    Codes are short-lived (10 min default) and single-use. The
    ``consume`` method is the only way to mark a code as used; callers
    must check ``consumed_at is None`` and ``expires_at > now`` first
    via ``get_active`` to avoid races.
    """

    @staticmethod
    def get_by_code(db: Session, *, code: str) -> ImBindingCode | None:
        if not code:
            return None
        stmt = select(ImBindingCode).where(ImBindingCode.code == code)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_active(db: Session, *, code: str) -> ImBindingCode | None:
        """Return the code if it exists, is unconsumed, and not yet expired.

        Does not lock the row — ``consume`` is the authoritative
        single-use guard via a conditional UPDATE.
        """
        now = datetime.now(timezone.utc)
        row = ImBindingCodeRepository.get_by_code(db, code=code)
        if row is None:
            return None
        if row.consumed_at is not None:
            return None
        if row.expires_at <= now:
            return None
        return row

    @staticmethod
    def create(
        db: Session,
        *,
        user_id: str,
        code: str,
        expires_at: datetime,
        provider: str | None = None,
    ) -> ImBindingCode:
        row = ImBindingCode(
            user_id=user_id,
            code=code,
            provider=provider,
            expires_at=expires_at,
        )
        db.add(row)
        return row

    @staticmethod
    def consume(
        db: Session,
        *,
        row: ImBindingCode,
        consumed_by: str,
    ) -> bool:
        """Mark a code as consumed. Returns True on success, False if it
        was already consumed or expired.

        Race-safe: the UPDATE is gated by ``consumed_at IS NULL`` and
        ``expires_at > now`` in the WHERE clause. The rowcount tells
        us whether this caller won the race; reading then mutating in
        Python would let two concurrent ``/bind`` requests both
        succeed, since both would observe ``consumed_at is None``.
        """
        now = datetime.now(timezone.utc)
        # Audit string is bounded by column length (255).
        consumed_by_value = (consumed_by or "")[:255]
        stmt = (
            update(ImBindingCode)
            .where(
                ImBindingCode.id == row.id,
                ImBindingCode.consumed_at.is_(None),
                ImBindingCode.expires_at > now,
            )
            .values(consumed_at=now, consumed_by=consumed_by_value)
        )
        result = db.connection().execute(stmt)
        db.flush()
        if result.rowcount == 0:
            # Lost the race (already consumed) or expired. Sync the
            # in-memory copy so callers see the truth without an extra
            # round trip.
            db.refresh(row)
            return False
        # Keep the in-memory instance consistent for downstream reads
        # in the same transaction.
        row.consumed_at = now
        row.consumed_by = consumed_by_value
        return True

    @staticmethod
    def delete_expired(db: Session) -> int:
        """Best-effort cleanup. Returns the number of rows deleted."""
        now = datetime.now(timezone.utc)
        stmt = select(ImBindingCode).where(ImBindingCode.expires_at < now)
        rows = list(db.execute(stmt).scalars().all())
        for row in rows:
            db.delete(row)
        return len(rows)
