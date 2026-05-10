import uuid

from sqlalchemy.orm import Session

from app.models.server_channel_agent_member import ServerChannelAgentMember


class ServerChannelAgentMemberRepository:
    @staticmethod
    def create(
        session_db: Session,
        membership: ServerChannelAgentMember,
    ) -> ServerChannelAgentMember:
        session_db.add(membership)
        return membership

    @staticmethod
    def get_by_channel_and_agent(
        session_db: Session,
        channel_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> ServerChannelAgentMember | None:
        return (
            session_db.query(ServerChannelAgentMember)
            .filter(
                ServerChannelAgentMember.channel_id == channel_id,
                ServerChannelAgentMember.agent_identity_id == agent_identity_id,
            )
            .first()
        )

    @staticmethod
    def list_by_channel(
        session_db: Session,
        channel_id: uuid.UUID,
    ) -> list[ServerChannelAgentMember]:
        return (
            session_db.query(ServerChannelAgentMember)
            .filter(ServerChannelAgentMember.channel_id == channel_id)
            .order_by(ServerChannelAgentMember.joined_at.asc())
            .all()
        )

    @staticmethod
    def list_by_agent(
        session_db: Session,
        agent_identity_id: uuid.UUID,
    ) -> list[ServerChannelAgentMember]:
        return (
            session_db.query(ServerChannelAgentMember)
            .filter(ServerChannelAgentMember.agent_identity_id == agent_identity_id)
            .order_by(ServerChannelAgentMember.joined_at.asc())
            .all()
        )

    @staticmethod
    def delete(
        session_db: Session,
        membership: ServerChannelAgentMember,
    ) -> None:
        session_db.delete(membership)
