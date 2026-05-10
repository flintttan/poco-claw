import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_persistent_state import AgentPersistentState
from app.repositories.agent_persistent_state_repository import (
    AgentPersistentStateRepository,
)


class AgentRuntimeService:
    @staticmethod
    def get_persistent_state(
        db: Session,
        agent_identity_id: uuid.UUID,
    ) -> AgentPersistentState:
        state = AgentPersistentStateRepository.get_by_agent_identity_id(
            db,
            agent_identity_id,
        )
        if state is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent persistent state not found: {agent_identity_id}",
            )
        return state

    def reserve_persistent_runtime(
        self,
        db: Session,
        *,
        agent_identity_id: uuid.UUID,
        session_id: uuid.UUID,
        channel_task_id: uuid.UUID | None,
    ) -> AgentPersistentState:
        state = self.get_persistent_state(db, agent_identity_id)
        if (
            state.runtime_status == "busy"
            and state.active_session_id is not None
            and state.active_session_id != session_id
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Agent persistent runtime is busy",
            )
        state.runtime_status = "busy"
        state.active_session_id = session_id
        state.active_task_id = channel_task_id
        state.last_synced_at = datetime.now(timezone.utc)
        return state

    def release_runtime_for_session(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        callback_status: str,
    ) -> AgentPersistentState | None:
        state = (
            db.query(AgentPersistentState)
            .filter(AgentPersistentState.active_session_id == session_id)
            .first()
        )
        if state is None:
            return None

        normalized = (callback_status or "").strip().lower()
        if normalized == "failed":
            state.runtime_status = "failed"
        else:
            state.runtime_status = "idle"
        state.active_session_id = None
        state.active_task_id = None
        state.last_synced_at = datetime.now(timezone.utc)
        state.last_written_at = datetime.now(timezone.utc)
        return state
