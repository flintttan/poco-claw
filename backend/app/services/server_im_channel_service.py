from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.im import Channel
from app.models.user import User
from app.repositories.im import ChannelRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.im_binding import ServerImChannelResponse, ServerImChannelUpdateRequest
from app.schemas.user_profile import UserPublicProfileResponse
from app.services.server_member_service import (
    require_server_admin,
    require_server_member,
)
from app.services.user_public_profile_service import list_user_public_profiles_by_id


class ServerImChannelService:
    """Server-scoped IM channel management.

    Read access is available to any active server member so collaborators can
    see which external chats are linked to the workspace. Mutating actions are
    restricted to server admins/owners because they change delivery behaviour
    for every participant in the linked chat.
    """

    @staticmethod
    def _require_server(db: Session, server_id: uuid.UUID) -> None:
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Server not found",
            )

    @staticmethod
    def _require_channel(
        db: Session,
        *,
        server_id: uuid.UUID,
        channel_id: int,
    ) -> Channel:
        channel = ChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Server IM channel not found",
            )
        return channel

    @staticmethod
    def _build_response(
        channel: Channel,
        *,
        user_profiles: dict[str, UserPublicProfileResponse],
    ) -> ServerImChannelResponse:
        return ServerImChannelResponse(
            id=channel.id,
            provider=channel.provider,
            destination=channel.destination,
            chat_type=channel.chat_type,
            enabled=channel.enabled,
            last_bound_by_user_id=channel.last_bound_by_user_id,
            last_bound_at=channel.last_bound_at,
            last_bound_by_user=user_profiles.get(channel.last_bound_by_user_id or ""),
        )

    def _build_responses(
        self,
        db: Session,
        channels: list[Channel],
    ) -> list[ServerImChannelResponse]:
        user_profiles = list_user_public_profiles_by_id(
            db,
            [channel.last_bound_by_user_id or "" for channel in channels],
        )
        return [
            self._build_response(channel, user_profiles=user_profiles)
            for channel in channels
        ]

    def list_channels(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> list[ServerImChannelResponse]:
        """Return all IM chats currently linked to ``server_id``."""
        self._require_server(db, server_id)
        require_server_member(db, server_id, current_user.id)
        channels = ChannelRepository.list_by_server(db, server_id=server_id)
        return self._build_responses(db, channels)

    def update_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: int,
        request: ServerImChannelUpdateRequest,
    ) -> ServerImChannelResponse:
        """Pause/resume delivery for one server-linked IM chat."""
        self._require_server(db, server_id)
        require_server_admin(db, server_id, current_user.id)
        channel = self._require_channel(db, server_id=server_id, channel_id=channel_id)
        channel.enabled = request.enabled
        db.commit()
        db.refresh(channel)
        return self._build_responses(db, [channel])[0]

    def unbind_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: int,
    ) -> None:
        """Remove the server binding from an IM chat.

        The chat record itself is retained so historical ownership / delivery
        state for the IM channel is not lost, but the server-scoped linkage is
        cleared entirely.
        """
        self._require_server(db, server_id)
        require_server_admin(db, server_id, current_user.id)
        channel = self._require_channel(db, server_id=server_id, channel_id=channel_id)
        channel.server_id = None
        channel.server_channel_id = None
        channel.last_bound_by_user_id = None
        channel.last_bound_at = None
        db.commit()
