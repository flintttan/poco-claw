import uuid

from sqlalchemy.orm import Session

from app.models.server_member import ServerMember


class ServerMemberRepository:
    @staticmethod
    def create(session_db: Session, membership: ServerMember) -> ServerMember:
        session_db.add(membership)
        return membership

    @staticmethod
    def get_by_server_and_user(
        session_db: Session,
        server_id: uuid.UUID,
        user_id: str,
    ) -> ServerMember | None:
        return (
            session_db.query(ServerMember)
            .filter(
                ServerMember.server_id == server_id,
                ServerMember.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def list_by_server(
        session_db: Session,
        server_id: uuid.UUID,
    ) -> list[ServerMember]:
        return (
            session_db.query(ServerMember)
            .filter(ServerMember.server_id == server_id)
            .order_by(ServerMember.joined_at.asc(), ServerMember.id.asc())
            .all()
        )

    @staticmethod
    def get_by_id(session_db: Session, membership_id: int) -> ServerMember | None:
        return (
            session_db.query(ServerMember)
            .filter(ServerMember.id == membership_id)
            .first()
        )
