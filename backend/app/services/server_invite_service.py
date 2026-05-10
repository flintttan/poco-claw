import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_invite import ServerInvite
from app.models.server_member import ServerMember
from app.models.user import User
from app.repositories.server_invite_repository import ServerInviteRepository
from app.repositories.server_member_repository import ServerMemberRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.server_invite import (
    ServerInviteAcceptRequest,
    ServerInviteCreateRequest,
    ServerInviteResponse,
    ServerInviteRevokeRequest,
)
from app.schemas.server_member import ServerMemberResponse
from app.services.server_member_service import require_server_admin


class ServerInviteService:
    @staticmethod
    def _stable_invite_token(server_id: uuid.UUID, user_id: str) -> str:
        digest = hashlib.sha256(f"{server_id}:{user_id}".encode("utf-8")).hexdigest()
        return f"srv_{digest[:32]}"

    @staticmethod
    def _build_invite_response(invite: ServerInvite) -> ServerInviteResponse:
        return ServerInviteResponse.model_validate(invite)

    def create_invite(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        request: ServerInviteCreateRequest,
    ) -> ServerInviteResponse:
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )
        require_server_admin(db, server_id, current_user.id)

        expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)
        token = self._stable_invite_token(server.id, current_user.id)
        invite = ServerInviteRepository.get_by_server_and_creator(
            db,
            server.id,
            current_user.id,
        )
        if invite is None:
            invite = ServerInviteRepository.create(
                db,
                ServerInvite(
                    server_id=server.id,
                    token=token,
                    role=request.role,
                    expires_at=expires_at,
                    created_by=current_user.id,
                    max_uses=request.max_uses,
                    used_count=0,
                ),
            )
        else:
            invite.token = token
            invite.role = request.role
            invite.expires_at = expires_at
            invite.max_uses = request.max_uses
            invite.used_count = 0
            invite.revoked_at = None
        db.commit()
        db.refresh(invite)
        return self._build_invite_response(invite)

    def list_invites(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> list[ServerInviteResponse]:
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )
        require_server_admin(db, server_id, current_user.id)
        invites = ServerInviteRepository.list_by_server(db, server_id)
        return [self._build_invite_response(item) for item in invites]

    def revoke_invite(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        invite_id: uuid.UUID,
        request: ServerInviteRevokeRequest,
    ) -> ServerInviteResponse:
        _ = request
        require_server_admin(db, server_id, current_user.id)
        invite = ServerInviteRepository.get_by_id(db, invite_id)
        if invite is None or invite.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server invite not found: {invite_id}",
            )
        invite.revoked_at = datetime.now(UTC)
        db.commit()
        return self._build_invite_response(invite)

    def accept_invite(
        self,
        db: Session,
        current_user: User,
        request: ServerInviteAcceptRequest,
    ) -> ServerMemberResponse:
        token = request.token.strip()
        invite = ServerInviteRepository.get_by_token(db, token)
        if invite is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Server invite not found",
            )
        server = ServerRepository.get_by_id(db, invite.server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {invite.server_id}",
            )
        if invite.revoked_at is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Server invite has been revoked",
            )
        if invite.expires_at < datetime.now(UTC):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Server invite has expired",
            )
        if invite.used_count >= invite.max_uses:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Server invite has already been used",
            )

        existing_membership = ServerMemberRepository.get_by_server_and_user(
            db,
            server.id,
            current_user.id,
        )
        if existing_membership is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="User is already a server member",
            )

        membership = ServerMemberRepository.create(
            db,
            ServerMember(
                server_id=server.id,
                user_id=current_user.id,
                role=invite.role,
                invited_by=invite.created_by,
                status="active",
            ),
        )
        invite.used_count += 1
        db.commit()
        if isinstance(membership, ServerMember):
            db.refresh(membership)
        return ServerMemberResponse.model_validate(membership)
