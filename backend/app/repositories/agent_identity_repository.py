import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.agent_identity import AgentIdentity


class AgentIdentityRepository:
    @staticmethod
    def create(session_db: Session, agent_identity: AgentIdentity) -> AgentIdentity:
        session_db.add(agent_identity)
        return agent_identity

    @staticmethod
    def get_by_id(
        session_db: Session,
        agent_identity_id: uuid.UUID,
    ) -> AgentIdentity | None:
        return (
            session_db.query(AgentIdentity)
            .options(joinedload(AgentIdentity.persistent_state))
            .filter(AgentIdentity.id == agent_identity_id)
            .first()
        )

    @staticmethod
    def get_by_server_and_handle(
        session_db: Session,
        server_id: uuid.UUID,
        handle: str,
        *,
        include_removed: bool = True,
    ) -> AgentIdentity | None:
        query = session_db.query(AgentIdentity).filter(
            AgentIdentity.server_id == server_id,
            AgentIdentity.handle == handle,
        )
        if not include_removed:
            query = query.filter(AgentIdentity.removed_at.is_(None))
        return query.first()

    @staticmethod
    def list_by_server(
        session_db: Session,
        server_id: uuid.UUID,
        *,
        include_removed: bool = False,
    ) -> list[AgentIdentity]:
        query = (
            session_db.query(AgentIdentity)
            .options(joinedload(AgentIdentity.persistent_state))
            .filter(AgentIdentity.server_id == server_id)
        )
        if not include_removed:
            query = query.filter(AgentIdentity.removed_at.is_(None))
        return query.order_by(
            AgentIdentity.created_at.asc(),
            AgentIdentity.display_name.asc(),
        ).all()

    @staticmethod
    def delete(session_db: Session, agent_identity: AgentIdentity) -> None:
        session_db.delete(agent_identity)
