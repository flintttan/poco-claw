import uuid

from sqlalchemy.orm import Session

from app.models.agent_persistent_state import AgentPersistentState


class AgentPersistentStateRepository:
    @staticmethod
    def create(
        session_db: Session,
        persistent_state: AgentPersistentState,
    ) -> AgentPersistentState:
        session_db.add(persistent_state)
        return persistent_state

    @staticmethod
    def get_by_agent_identity_id(
        session_db: Session,
        agent_identity_id: uuid.UUID,
    ) -> AgentPersistentState | None:
        return (
            session_db.query(AgentPersistentState)
            .filter(AgentPersistentState.agent_identity_id == agent_identity_id)
            .first()
        )
