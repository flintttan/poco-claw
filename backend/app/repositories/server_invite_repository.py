import uuid

from sqlalchemy.orm import Session

from app.models.server_invite import ServerInvite


class ServerInviteRepository:
    @staticmethod
    def create(session_db: Session, invite: ServerInvite) -> ServerInvite:
        session_db.add(invite)
        return invite

    @staticmethod
    def get_by_token(session_db: Session, token: str) -> ServerInvite | None:
        return (
            session_db.query(ServerInvite).filter(ServerInvite.token == token).first()
        )

    @staticmethod
    def get_by_server_and_creator(
        session_db: Session,
        server_id: uuid.UUID,
        created_by: str,
    ) -> ServerInvite | None:
        return (
            session_db.query(ServerInvite)
            .filter(
                ServerInvite.server_id == server_id,
                ServerInvite.created_by == created_by,
            )
            .first()
        )

    @staticmethod
    def list_by_server(
        session_db: Session,
        server_id: uuid.UUID,
    ) -> list[ServerInvite]:
        return (
            session_db.query(ServerInvite)
            .filter(ServerInvite.server_id == server_id)
            .order_by(ServerInvite.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(
        session_db: Session,
        invite_id: uuid.UUID,
    ) -> ServerInvite | None:
        return (
            session_db.query(ServerInvite).filter(ServerInvite.id == invite_id).first()
        )
