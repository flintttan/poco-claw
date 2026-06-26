import uuid

from sqlalchemy.orm import Session

from app.models.server import Server
from app.models.server_member import ServerMember


class ServerRepository:
    @staticmethod
    def create(session_db: Session, server: Server) -> Server:
        session_db.add(server)
        return server

    @staticmethod
    def get_by_id(
        session_db: Session,
        server_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> Server | None:
        query = session_db.query(Server).filter(Server.id == server_id)
        if not include_deleted:
            query = query.filter(Server.is_deleted.is_(False))
        return query.first()

    @staticmethod
    def list_by_ids(
        session_db: Session,
        server_ids: list[uuid.UUID] | set[uuid.UUID] | tuple[uuid.UUID, ...],
        *,
        include_deleted: bool = False,
    ) -> list[Server]:
        """Batch fetch servers by primary key.

        Mirrors :func:`ChannelRepository.list_by_ids` — used by the
        multi-channel event router to avoid an N+1 query when
        resolving the soft-deleted state of every bound server.
        An empty input returns an empty list without hitting the DB.
        """
        if not server_ids:
            return []
        query = session_db.query(Server).filter(Server.id.in_(server_ids))
        if not include_deleted:
            query = query.filter(Server.is_deleted.is_(False))
        return query.all()

    @staticmethod
    def get_by_slug(session_db: Session, slug: str) -> Server | None:
        return (
            session_db.query(Server)
            .filter(Server.slug == slug, Server.is_deleted.is_(False))
            .first()
        )

    @staticmethod
    def get_personal_by_owner(
        session_db: Session,
        owner_user_id: str,
    ) -> Server | None:
        return (
            session_db.query(Server)
            .filter(
                Server.owner_user_id == owner_user_id,
                Server.kind == "personal",
                Server.is_deleted.is_(False),
            )
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, user_id: str) -> list[Server]:
        return (
            session_db.query(Server)
            .join(ServerMember, ServerMember.server_id == Server.id)
            .filter(
                ServerMember.user_id == user_id,
                ServerMember.status == "active",
                Server.is_deleted.is_(False),
            )
            .order_by(Server.created_at.desc())
            .all()
        )
