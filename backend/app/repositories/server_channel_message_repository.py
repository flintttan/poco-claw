import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.server_channel_message import ServerChannelMessage


class ServerChannelMessageRepository:
    @staticmethod
    def create(
        session_db: Session,
        message: ServerChannelMessage,
    ) -> ServerChannelMessage:
        session_db.add(message)
        return message

    @staticmethod
    def get_by_id(
        session_db: Session,
        message_id: uuid.UUID,
    ) -> ServerChannelMessage | None:
        return (
            session_db.query(ServerChannelMessage)
            .filter(ServerChannelMessage.id == message_id)
            .first()
        )

    @staticmethod
    def list_by_channel(
        session_db: Session,
        channel_id: uuid.UUID,
        *,
        before_message_id: uuid.UUID | None = None,
        limit: int | None = 50,
    ) -> list[ServerChannelMessage]:
        query = session_db.query(ServerChannelMessage).filter(
            ServerChannelMessage.channel_id == channel_id,
            ServerChannelMessage.thread_root_message_id.is_(None),
        )
        if before_message_id is not None:
            before = ServerChannelMessageRepository.get_by_id(
                session_db,
                before_message_id,
            )
            if before is not None:
                query = query.filter(
                    ServerChannelMessage.created_at < before.created_at
                )
        query = query.order_by(
            ServerChannelMessage.created_at.desc(),
            ServerChannelMessage.id.desc(),
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def list_all_by_channel(
        session_db: Session,
        channel_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> list[ServerChannelMessage]:
        query = (
            session_db.query(ServerChannelMessage)
            .filter(ServerChannelMessage.channel_id == channel_id)
            .order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def list_from_anchor(
        session_db: Session,
        channel_id: uuid.UUID,
        *,
        anchor_message: ServerChannelMessage,
        direction: str,
        limit: int = 50,
    ) -> list[ServerChannelMessage]:
        query = session_db.query(ServerChannelMessage).filter(
            ServerChannelMessage.channel_id == channel_id,
            ServerChannelMessage.thread_root_message_id.is_(None),
        )
        if direction == "after":
            query = query.filter(
                or_(
                    ServerChannelMessage.created_at > anchor_message.created_at,
                    (ServerChannelMessage.created_at == anchor_message.created_at)
                    & (ServerChannelMessage.id > anchor_message.id),
                )
            ).order_by(
                ServerChannelMessage.created_at.asc(),
                ServerChannelMessage.id.asc(),
            )
        else:
            query = query.filter(
                or_(
                    ServerChannelMessage.created_at < anchor_message.created_at,
                    (ServerChannelMessage.created_at == anchor_message.created_at)
                    & (ServerChannelMessage.id < anchor_message.id),
                )
            ).order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
        return query.limit(limit).all()

    @staticmethod
    def list_replies(
        session_db: Session,
        thread_root_message_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[ServerChannelMessage]:
        return (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.thread_root_message_id == thread_root_message_id,
            )
            .order_by(
                ServerChannelMessage.created_at.asc(),
                ServerChannelMessage.id.asc(),
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_replies_by_roots(
        session_db: Session,
        root_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        if not root_ids:
            return {}
        rows = (
            session_db.query(
                ServerChannelMessage.thread_root_message_id,
                func.count(ServerChannelMessage.id),
            )
            .filter(ServerChannelMessage.thread_root_message_id.in_(root_ids))
            .group_by(ServerChannelMessage.thread_root_message_id)
            .all()
        )
        return {root_id: count for root_id, count in rows if root_id is not None}

    @staticmethod
    def get_oldest_open_execution_placeholder(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ServerChannelMessage | None:
        candidates = (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.channel_id == channel_id,
                ServerChannelMessage.message_type == "system",
            )
            .order_by(
                ServerChannelMessage.created_at.asc(),
                ServerChannelMessage.id.asc(),
            )
            .all()
        )
        session_id_text = str(session_id)
        for candidate in candidates:
            content = candidate.content or {}
            if content.get("source") != "agent_execution":
                continue
            if str(content.get("session_id") or "").strip() != session_id_text:
                continue
            status = str(content.get("execution_status") or "").strip().lower()
            if status in {"completed", "failed", "canceled", "cancelled"}:
                continue
            return candidate
        return None

    @staticmethod
    def get_latest_execution_placeholder(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ServerChannelMessage | None:
        candidates = (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.channel_id == channel_id,
                ServerChannelMessage.message_type == "system",
            )
            .order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
            .all()
        )
        session_id_text = str(session_id)
        for candidate in candidates:
            content = candidate.content or {}
            if content.get("source") != "agent_execution":
                continue
            if str(content.get("session_id") or "").strip() != session_id_text:
                continue
            return candidate
        return None

    @staticmethod
    def get_latest_session_projection(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ServerChannelMessage | None:
        candidates = (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.channel_id == channel_id,
                ServerChannelMessage.message_type == "system",
            )
            .order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
            .all()
        )
        session_id_text = str(session_id)
        for candidate in candidates:
            content = candidate.content or {}
            if content.get("source") not in {"agent_execution", "agent_session"}:
                continue
            if str(content.get("session_id") or "").strip() != session_id_text:
                continue
            return candidate
        return None

    @staticmethod
    def list_session_projections(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        session_id: uuid.UUID,
        open_only: bool = False,
    ) -> list[ServerChannelMessage]:
        candidates = (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.channel_id == channel_id,
                ServerChannelMessage.message_type == "system",
            )
            .order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
            .all()
        )
        session_id_text = str(session_id)
        results: list[ServerChannelMessage] = []
        for candidate in candidates:
            content = candidate.content or {}
            source = content.get("source")
            if source not in {"agent_execution", "agent_session"}:
                continue
            if str(content.get("session_id") or "").strip() != session_id_text:
                continue
            if open_only:
                status = str(content.get("execution_status") or "").strip().lower()
                if status in {"completed", "failed", "canceled", "cancelled"}:
                    continue
            results.append(candidate)
        return results

    @staticmethod
    def find_execution_placeholder(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        session_id: uuid.UUID,
        projection_message_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        queue_item_id: uuid.UUID | None = None,
        trigger_message_id: uuid.UUID | None = None,
        thread_root_message_id: uuid.UUID | None = None,
        open_only: bool = False,
    ) -> ServerChannelMessage | None:
        candidates = (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.channel_id == channel_id,
                ServerChannelMessage.message_type == "system",
            )
            .order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
            .all()
        )
        session_id_text = str(session_id)
        projection_message_id_text = (
            str(projection_message_id) if projection_message_id else None
        )
        run_id_text = str(run_id) if run_id else None
        queue_item_id_text = str(queue_item_id) if queue_item_id else None
        trigger_message_id_text = (
            str(trigger_message_id) if trigger_message_id else None
        )
        thread_root_message_id_text = (
            str(thread_root_message_id) if thread_root_message_id else None
        )

        def matches_open(candidate: ServerChannelMessage) -> bool:
            content = candidate.content or {}
            status = str(content.get("execution_status") or "").strip().lower()
            return status not in {"completed", "failed", "canceled", "cancelled"}

        filtered: list[ServerChannelMessage] = []
        for candidate in candidates:
            content = candidate.content or {}
            if content.get("source") != "agent_execution":
                continue
            if str(content.get("session_id") or "").strip() != session_id_text:
                continue
            if open_only and not matches_open(candidate):
                continue
            filtered.append(candidate)

        if projection_message_id_text:
            for candidate in filtered:
                if str(candidate.id) == projection_message_id_text:
                    return candidate

        if run_id_text:
            for candidate in filtered:
                content = candidate.content or {}
                if str(content.get("run_id") or "").strip() == run_id_text:
                    return candidate

        if queue_item_id_text:
            for candidate in filtered:
                content = candidate.content or {}
                if (
                    str(content.get("queue_item_id") or "").strip()
                    == queue_item_id_text
                ):
                    return candidate

        if trigger_message_id_text or thread_root_message_id_text:
            for candidate in filtered:
                content = candidate.content or {}
                candidate_trigger = str(content.get("trigger_message_id") or "").strip()
                candidate_thread = str(
                    content.get("thread_root_message_id") or ""
                ).strip()
                if (
                    trigger_message_id_text
                    and candidate_trigger != trigger_message_id_text
                ):
                    continue
                if (
                    thread_root_message_id_text
                    and candidate_thread != thread_root_message_id_text
                ):
                    continue
                return candidate

        if (
            projection_message_id_text
            or run_id_text
            or queue_item_id_text
            or trigger_message_id_text
            or thread_root_message_id_text
        ):
            return None

        return filtered[0] if filtered else None

    @staticmethod
    def find_session_projection_by_run(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        session_id: uuid.UUID,
        projection_message_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        queue_item_id: uuid.UUID | None = None,
    ) -> ServerChannelMessage | None:
        candidates = (
            session_db.query(ServerChannelMessage)
            .filter(
                ServerChannelMessage.channel_id == channel_id,
                ServerChannelMessage.message_type == "system",
            )
            .order_by(
                ServerChannelMessage.created_at.desc(),
                ServerChannelMessage.id.desc(),
            )
            .all()
        )
        session_id_text = str(session_id)
        projection_message_id_text = (
            str(projection_message_id) if projection_message_id else None
        )
        run_id_text = str(run_id) if run_id else None
        queue_item_id_text = str(queue_item_id) if queue_item_id else None
        for candidate in candidates:
            content = candidate.content or {}
            if content.get("source") not in {"agent_execution", "agent_session"}:
                continue
            if str(content.get("session_id") or "").strip() != session_id_text:
                continue
            if (
                projection_message_id_text
                and str(candidate.id) == projection_message_id_text
            ):
                return candidate
            if run_id_text and str(content.get("run_id") or "").strip() == run_id_text:
                return candidate
            if (
                queue_item_id_text
                and str(content.get("queue_item_id") or "").strip()
                == queue_item_id_text
            ):
                return candidate
        return None

    @staticmethod
    def list_open_execution_placeholders_by_agent_scope(
        session_db: Session,
        *,
        agent_identity_id: uuid.UUID,
        channel_id: uuid.UUID | None = None,
    ) -> list[ServerChannelMessage]:
        query = session_db.query(ServerChannelMessage).filter(
            ServerChannelMessage.message_type == "system",
        )
        if channel_id is not None:
            query = query.filter(ServerChannelMessage.channel_id == channel_id)
        candidates = query.order_by(
            ServerChannelMessage.created_at.desc(),
            ServerChannelMessage.id.desc(),
        ).all()
        agent_identity_id_text = str(agent_identity_id)
        results: list[ServerChannelMessage] = []
        for candidate in candidates:
            content = candidate.content or {}
            if content.get("source") != "agent_execution":
                continue
            if (
                str(content.get("agent_identity_id") or "").strip()
                != agent_identity_id_text
            ):
                continue
            status = str(content.get("execution_status") or "").strip().lower()
            if status in {"completed", "failed", "canceled", "cancelled"}:
                continue
            results.append(candidate)
        return results
