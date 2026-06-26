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
    def list_active_by_user_and_servers(
        session_db: Session,
        *,
        user_id: str,
        server_ids: list[uuid.UUID] | set[uuid.UUID] | tuple[uuid.UUID, ...],
    ) -> list[ServerMember]:
        """Batch fetch active memberships for ``user_id`` across multiple servers.

        Used by the multi-channel event router so that N server-bound
        channels do not produce N individual ``get_by_server_and_user``
        queries. An empty input returns an empty list without hitting
        the database.
        """
        if not server_ids:
            return []
        return (
            session_db.query(ServerMember)
            .filter(
                ServerMember.user_id == user_id,
                ServerMember.server_id.in_(server_ids),
                ServerMember.status == "active",
            )
            .all()
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
