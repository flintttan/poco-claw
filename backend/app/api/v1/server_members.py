import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.server_member import (
    ServerMemberResponse,
    ServerMemberRoleUpdateRequest,
)
from app.services.server_member_service import ServerMemberService

router = APIRouter(prefix="/servers/{server_id}/members", tags=["server-members"])

service = ServerMemberService()


@router.get("", response_model=ResponseSchema[list[ServerMemberResponse]])
async def list_server_members(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_members(db, current_user, server_id)
    return Response.success(
        data=result,
        message="Server members retrieved successfully",
    )


@router.patch(
    "/{membership_id}/role", response_model=ResponseSchema[ServerMemberResponse]
)
async def update_server_member_role(
    server_id: uuid.UUID,
    membership_id: int,
    request: ServerMemberRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_member_role(
        db,
        current_user,
        server_id,
        membership_id,
        request,
    )
    return Response.success(
        data=result,
        message="Server member role updated successfully",
    )


@router.delete("/{membership_id}", response_model=ResponseSchema[dict])
async def remove_server_member(
    server_id: uuid.UUID,
    membership_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.remove_member(db, current_user, server_id, membership_id)
    return Response.success(
        data={"id": membership_id},
        message="Server member removed successfully",
    )


@router.post("/leave", response_model=ResponseSchema[dict])
async def leave_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.leave_server(db, current_user, server_id)
    return Response.success(
        data={"server_id": server_id},
        message="Server left successfully",
    )
