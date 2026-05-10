import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.session_repository import SessionRepository
from app.schemas.channel_runtime import AgentChannelRuntimeScope


class ChannelRuntimeScopeService:
    def resolve_scope(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> AgentChannelRuntimeScope:
        session = SessionRepository.get_by_id(db, session_id)
        if session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )

        snapshot = session.config_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}

        trigger_context = snapshot.get("trigger_context")
        if not isinstance(trigger_context, dict):
            trigger_context = {}

        server_id = self._required_uuid(snapshot, "server_id")
        channel_id = self._required_uuid(snapshot, "channel_id")
        agent_identity_id = self._required_uuid(snapshot, "agent_identity_id")

        agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if (
            agent is None
            or agent.server_id != server_id
            or agent.lifecycle_state != "active"
        ):
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )

        membership = ServerChannelAgentMemberRepository.get_by_channel_and_agent(
            db,
            channel_id=channel_id,
            agent_identity_id=agent_identity_id,
        )
        if membership is None or membership.status != "active":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Agent is not an active member of this channel",
            )

        handoff = trigger_context.get("handoff")
        if not isinstance(handoff, dict):
            handoff = {}

        return AgentChannelRuntimeScope(
            session_id=session.id,
            user_id=session.user_id,
            server_id=server_id,
            channel_id=channel_id,
            agent_identity_id=agent_identity_id,
            agent_handle=(agent.handle or "").strip() or str(agent.id),
            agent_label=(agent.display_name or "").strip()
            or (agent.handle or "").strip()
            or "Agent",
            agent_preset_id=agent.preset_id,
            trigger_message_id=self._optional_uuid(
                snapshot.get("trigger_message_id")
                or trigger_context.get("trigger_message_id")
            ),
            thread_root_message_id=self._optional_uuid(
                snapshot.get("thread_root_message_id")
                or trigger_context.get("thread_root_message_id")
            ),
            parent_run_id=self._optional_uuid(
                snapshot.get("run_id") or handoff.get("parent_run_id")
            ),
            handoff_depth=self._safe_depth(handoff.get("depth")),
            trigger_context=trigger_context,
        )

    @staticmethod
    def _optional_uuid(value: Any) -> uuid.UUID | None:
        if value is None:
            return None
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _required_uuid(cls, snapshot: dict[str, Any], key: str) -> uuid.UUID:
        value = cls._optional_uuid(snapshot.get(key))
        if value is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session is missing channel runtime context",
            )
        return value

    @staticmethod
    def _safe_depth(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0
