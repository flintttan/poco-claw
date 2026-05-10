import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.repositories.server_member_repository import ServerMemberRepository
from app.schemas.server_member import (
    ServerMemberResponse,
    ServerMemberRoleUpdateRequest,
)
from app.services.user_public_profile_service import list_user_public_profiles_by_id


def _require_active_membership(db: Session, server_id: uuid.UUID, user_id: str):
    membership = ServerMemberRepository.get_by_server_and_user(
        db,
        server_id,
        user_id,
    )
    if membership is None or membership.status != "active":
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="You are not a member of this server",
        )
    return membership


def require_server_member(db: Session, server_id: uuid.UUID, user_id: str):
    return _require_active_membership(db, server_id, user_id)


def require_server_admin(db: Session, server_id: uuid.UUID, user_id: str):
    membership = _require_active_membership(db, server_id, user_id)
    if membership.role not in {"owner", "admin"}:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="You do not have admin access to this server",
        )
    return membership


def require_server_owner(db: Session, server_id: uuid.UUID, user_id: str):
    membership = _require_active_membership(db, server_id, user_id)
    if membership.role != "owner":
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Only server owners can perform this action",
        )
    return membership


class ServerMemberService:
    def list_members(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> list[ServerMemberResponse]:
        require_server_member(db, server_id, current_user.id)
        members = ServerMemberRepository.list_by_server(db, server_id)
        user_profiles = list_user_public_profiles_by_id(
            db,
            [member.user_id for member in members],
        )
        return [
            ServerMemberResponse.model_validate(item).model_copy(
                update={"user": user_profiles.get(item.user_id)}
            )
            for item in members
        ]

    def update_member_role(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        membership_id: int,
        request: ServerMemberRoleUpdateRequest,
    ) -> ServerMemberResponse:
        require_server_owner(db, server_id, current_user.id)
        membership = ServerMemberRepository.get_by_id(db, membership_id)
        if membership is None or membership.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server membership not found: {membership_id}",
            )
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Owner role cannot be changed directly",
            )
        membership.role = request.role
        db.commit()
        user_profiles = list_user_public_profiles_by_id(db, [membership.user_id])
        return ServerMemberResponse.model_validate(membership).model_copy(
            update={"user": user_profiles.get(membership.user_id)}
        )

    def remove_member(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        membership_id: int,
    ) -> None:
        require_server_owner(db, server_id, current_user.id)
        membership = ServerMemberRepository.get_by_id(db, membership_id)
        if membership is None or membership.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server membership not found: {membership_id}",
            )
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Server owner cannot be removed",
            )
        db.delete(membership)
        db.commit()

    def leave_server(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> None:
        membership = require_server_member(db, server_id, current_user.id)
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Server owner cannot leave without transferring ownership",
            )
        db.delete(membership)
        db.commit()
