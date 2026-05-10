import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.server_channel_message_reaction import ServerChannelMessageReaction


class ServerChannelMessageReactionRepository:
    @staticmethod
    def get_user_reaction(
        session_db: Session,
        *,
        message_id: uuid.UUID,
        emoji: str,
        actor_user_id: str,
    ) -> ServerChannelMessageReaction | None:
        return (
            session_db.query(ServerChannelMessageReaction)
            .filter(
                ServerChannelMessageReaction.message_id == message_id,
                ServerChannelMessageReaction.emoji == emoji,
                ServerChannelMessageReaction.actor_type == "user",
                ServerChannelMessageReaction.actor_user_id == actor_user_id,
            )
            .first()
        )

    @staticmethod
    def get_agent_reaction(
        session_db: Session,
        *,
        message_id: uuid.UUID,
        emoji: str,
        actor_agent_identity_id: uuid.UUID,
    ) -> ServerChannelMessageReaction | None:
        return (
            session_db.query(ServerChannelMessageReaction)
            .filter(
                ServerChannelMessageReaction.message_id == message_id,
                ServerChannelMessageReaction.emoji == emoji,
                ServerChannelMessageReaction.actor_type == "agent",
                ServerChannelMessageReaction.actor_agent_identity_id
                == actor_agent_identity_id,
            )
            .first()
        )

    @staticmethod
    def create(
        session_db: Session,
        reaction: ServerChannelMessageReaction,
    ) -> ServerChannelMessageReaction:
        session_db.add(reaction)
        return reaction

    @staticmethod
    def delete(
        session_db: Session,
        reaction: ServerChannelMessageReaction,
    ) -> None:
        session_db.delete(reaction)

    @staticmethod
    def list_by_messages(
        session_db: Session,
        message_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[ServerChannelMessageReaction]]:
        if not message_ids:
            return {}
        reactions = (
            session_db.query(ServerChannelMessageReaction)
            .filter(ServerChannelMessageReaction.message_id.in_(message_ids))
            .order_by(
                ServerChannelMessageReaction.created_at.asc(),
                ServerChannelMessageReaction.id.asc(),
            )
            .all()
        )
        grouped: dict[uuid.UUID, list[ServerChannelMessageReaction]] = defaultdict(list)
        for reaction in reactions:
            grouped[reaction.message_id].append(reaction)
        return dict(grouped)
