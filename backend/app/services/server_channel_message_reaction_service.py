import re
import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_identity import AgentIdentity
from app.models.server_channel_message import ServerChannelMessage
from app.models.server_channel_message_reaction import ServerChannelMessageReaction
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.server_channel_message_reaction_repository import (
    ServerChannelMessageReactionRepository,
)
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.session_repository import SessionRepository
from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionActorResponse,
    ServerChannelMessageReactionGroupResponse,
    ServerChannelMessageReactionOperationResponse,
)
from app.schemas.user_profile import UserPublicProfileResponse
from app.services.server_channel_message_service import ServerChannelMessageService
from app.services.user_public_profile_service import list_user_public_profiles_by_id


class ServerChannelMessageReactionService:
    MAX_ACTOR_PREVIEW = 5
    _URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)

    def __init__(self) -> None:
        self._message_service = ServerChannelMessageService()

    @classmethod
    def normalize_emoji(cls, emoji: str) -> str:
        normalized = emoji.strip()
        if not normalized:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Emoji must not be empty",
            )
        if len(normalized) > 32:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Emoji is too long",
            )
        if cls._URL_PATTERN.match(normalized) or normalized.isascii():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Emoji must be a Unicode emoji sequence",
            )
        return normalized

    @staticmethod
    def _require_message_in_channel(
        db: Session,
        *,
        message_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> ServerChannelMessage:
        message = ServerChannelMessageRepository.get_by_id(db, message_id)
        if message is None or message.channel_id != channel_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Message not found: {message_id}",
            )
        return message

    @staticmethod
    def _resolve_runtime_scope(
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        db_session = SessionRepository.get_by_id(db, session_id)
        if db_session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )

        snapshot = db_session.config_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        try:
            server_id = uuid.UUID(str(snapshot.get("server_id")))
            channel_id = uuid.UUID(str(snapshot.get("channel_id")))
            agent_identity_id = uuid.UUID(str(snapshot.get("agent_identity_id")))
        except (TypeError, ValueError):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session is missing channel reaction runtime context",
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
        return server_id, channel_id, agent_identity_id

    def add_user_reaction(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        message_id: uuid.UUID,
        emoji: str,
    ) -> ServerChannelMessageReactionOperationResponse:
        channel = self._message_service._require_channel_access(
            db,
            current_user,
            server_id,
            channel_id,
        )
        message = self._require_message_in_channel(
            db,
            message_id=message_id,
            channel_id=channel.id,
        )
        normalized = self.normalize_emoji(emoji)
        reaction = ServerChannelMessageReactionRepository.get_user_reaction(
            db,
            message_id=message.id,
            emoji=normalized,
            actor_user_id=current_user.id,
        )
        if reaction is None:
            ServerChannelMessageReactionRepository.create(
                db,
                ServerChannelMessageReaction(
                    message_id=message.id,
                    channel_id=channel.id,
                    emoji=normalized,
                    actor_type="user",
                    actor_user_id=current_user.id,
                ),
            )
        db.commit()
        return self._build_operation_response(
            db,
            action="add_channel_message_reaction",
            message_id=message.id,
            emoji=normalized,
            current_user_id=current_user.id,
        )

    def remove_user_reaction(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        message_id: uuid.UUID,
        emoji: str,
    ) -> ServerChannelMessageReactionOperationResponse:
        channel = self._message_service._require_channel_access(
            db,
            current_user,
            server_id,
            channel_id,
        )
        message = self._require_message_in_channel(
            db,
            message_id=message_id,
            channel_id=channel.id,
        )
        normalized = self.normalize_emoji(emoji)
        reaction = ServerChannelMessageReactionRepository.get_user_reaction(
            db,
            message_id=message.id,
            emoji=normalized,
            actor_user_id=current_user.id,
        )
        if reaction is not None:
            ServerChannelMessageReactionRepository.delete(db, reaction)
        db.commit()
        return self._build_operation_response(
            db,
            action="remove_channel_message_reaction",
            message_id=message.id,
            emoji=normalized,
            current_user_id=current_user.id,
        )

    def add_agent_reaction(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        emoji: str,
    ) -> ServerChannelMessageReactionOperationResponse:
        _, channel_id, agent_identity_id = self._resolve_runtime_scope(
            db,
            session_id=session_id,
        )
        message = self._require_message_in_channel(
            db,
            message_id=message_id,
            channel_id=channel_id,
        )
        normalized = self.normalize_emoji(emoji)
        reaction = ServerChannelMessageReactionRepository.get_agent_reaction(
            db,
            message_id=message.id,
            emoji=normalized,
            actor_agent_identity_id=agent_identity_id,
        )
        if reaction is None:
            ServerChannelMessageReactionRepository.create(
                db,
                ServerChannelMessageReaction(
                    message_id=message.id,
                    channel_id=channel_id,
                    emoji=normalized,
                    actor_type="agent",
                    actor_agent_identity_id=agent_identity_id,
                ),
            )
        db.commit()
        return self._build_operation_response(
            db,
            action="add_channel_message_reaction",
            message_id=message.id,
            emoji=normalized,
            current_agent_identity_id=agent_identity_id,
        )

    def remove_agent_reaction(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        emoji: str,
    ) -> ServerChannelMessageReactionOperationResponse:
        _, channel_id, agent_identity_id = self._resolve_runtime_scope(
            db,
            session_id=session_id,
        )
        message = self._require_message_in_channel(
            db,
            message_id=message_id,
            channel_id=channel_id,
        )
        normalized = self.normalize_emoji(emoji)
        reaction = ServerChannelMessageReactionRepository.get_agent_reaction(
            db,
            message_id=message.id,
            emoji=normalized,
            actor_agent_identity_id=agent_identity_id,
        )
        if reaction is not None:
            ServerChannelMessageReactionRepository.delete(db, reaction)
        db.commit()
        return self._build_operation_response(
            db,
            action="remove_channel_message_reaction",
            message_id=message.id,
            emoji=normalized,
            current_agent_identity_id=agent_identity_id,
        )

    def list_grouped_by_messages(
        self,
        db: Session,
        message_ids: list[uuid.UUID],
        *,
        current_user_id: str | None = None,
        current_agent_identity_id: uuid.UUID | None = None,
    ) -> dict[uuid.UUID, list[ServerChannelMessageReactionGroupResponse]]:
        reactions_by_message = ServerChannelMessageReactionRepository.list_by_messages(
            db,
            message_ids,
        )
        user_profiles = self._load_user_profiles(db, reactions_by_message)
        agent_profiles = self._load_agent_profiles(db, reactions_by_message)
        return {
            message_id: self._build_groups(
                reactions,
                user_profiles=user_profiles,
                agent_profiles=agent_profiles,
                current_user_id=current_user_id,
                current_agent_identity_id=current_agent_identity_id,
            )
            for message_id, reactions in reactions_by_message.items()
        }

    def _build_operation_response(
        self,
        db: Session,
        *,
        action: str,
        message_id: uuid.UUID,
        emoji: str,
        current_user_id: str | None = None,
        current_agent_identity_id: uuid.UUID | None = None,
    ) -> ServerChannelMessageReactionOperationResponse:
        groups = self.list_grouped_by_messages(
            db,
            [message_id],
            current_user_id=current_user_id,
            current_agent_identity_id=current_agent_identity_id,
        ).get(message_id, [])
        return ServerChannelMessageReactionOperationResponse(
            action=action,
            message_id=message_id,
            reaction=next((group for group in groups if group.emoji == emoji), None),
        )

    @staticmethod
    def _load_user_profiles(
        db: Session,
        reactions_by_message: dict[uuid.UUID, list[ServerChannelMessageReaction]],
    ) -> dict[str, UserPublicProfileResponse]:
        user_ids = {
            reaction.actor_user_id
            for reactions in reactions_by_message.values()
            for reaction in reactions
            if reaction.actor_user_id is not None
        }
        return list_user_public_profiles_by_id(db, list(user_ids))

    @staticmethod
    def _load_agent_profiles(
        db: Session,
        reactions_by_message: dict[uuid.UUID, list[ServerChannelMessageReaction]],
    ) -> dict[uuid.UUID, AgentIdentity]:
        agent_ids = {
            reaction.actor_agent_identity_id
            for reactions in reactions_by_message.values()
            for reaction in reactions
            if reaction.actor_agent_identity_id is not None
        }
        agents: dict[uuid.UUID, AgentIdentity] = {}
        for agent_id in agent_ids:
            agent = AgentIdentityRepository.get_by_id(db, agent_id)
            if agent is not None:
                agents[agent.id] = agent
        return agents

    def _build_groups(
        self,
        reactions: list[ServerChannelMessageReaction],
        *,
        user_profiles: dict[str, UserPublicProfileResponse],
        agent_profiles: dict[uuid.UUID, AgentIdentity],
        current_user_id: str | None,
        current_agent_identity_id: uuid.UUID | None,
    ) -> list[ServerChannelMessageReactionGroupResponse]:
        grouped: dict[str, list[ServerChannelMessageReaction]] = defaultdict(list)
        for reaction in reactions:
            grouped[reaction.emoji].append(reaction)

        groups: list[ServerChannelMessageReactionGroupResponse] = []
        for emoji, items in grouped.items():
            actors = [
                self._build_actor_response(
                    reaction,
                    user_profiles=user_profiles,
                    agent_profiles=agent_profiles,
                )
                for reaction in items[: self.MAX_ACTOR_PREVIEW]
            ]
            groups.append(
                ServerChannelMessageReactionGroupResponse(
                    emoji=emoji,
                    count=len(items),
                    reacted_by_current_user=any(
                        item.actor_type == "user"
                        and item.actor_user_id == current_user_id
                        for item in items
                    ),
                    reacted_by_current_agent=any(
                        item.actor_type == "agent"
                        and item.actor_agent_identity_id == current_agent_identity_id
                        for item in items
                    ),
                    actors=actors,
                )
            )
        return groups

    @staticmethod
    def _build_actor_response(
        reaction: ServerChannelMessageReaction,
        *,
        user_profiles: dict[str, UserPublicProfileResponse],
        agent_profiles: dict[uuid.UUID, AgentIdentity],
    ) -> ServerChannelMessageReactionActorResponse:
        if reaction.actor_type == "agent" and reaction.actor_agent_identity_id:
            agent = agent_profiles.get(reaction.actor_agent_identity_id)
            return ServerChannelMessageReactionActorResponse(
                actor_type="agent",
                agent_identity_id=reaction.actor_agent_identity_id,
                agent_handle=agent.handle if agent else None,
                agent_label=agent.display_name if agent else None,
            )
        return ServerChannelMessageReactionActorResponse(
            actor_type="user",
            user_id=reaction.actor_user_id,
            user=user_profiles.get(reaction.actor_user_id or ""),
        )
