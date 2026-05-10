import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.server_invite import (
    ServerInviteAcceptRequest,
    ServerInviteCreateRequest,
    ServerInviteResponse,
    ServerInviteRevokeRequest,
)
from app.schemas.server_member import ServerMemberResponse
from app.services.server_invite_service import ServerInviteService

router = APIRouter(prefix="/servers/{server_id}/invites", tags=["server-invites"])
accept_router = APIRouter(prefix="/server-invites", tags=["server-invites"])

service = ServerInviteService()


@router.get("", response_model=ResponseSchema[list[ServerInviteResponse]])
async def list_server_invites(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_invites(db, current_user, server_id)
    return Response.success(
        data=result,
        message="Server invites retrieved successfully",
    )


@router.post("", response_model=ResponseSchema[ServerInviteResponse])
async def create_server_invite(
    server_id: uuid.UUID,
    request: ServerInviteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_invite(db, current_user, server_id, request)
    return Response.success(data=result, message="Server invite created successfully")


@router.post("/{invite_id}/revoke", response_model=ResponseSchema[ServerInviteResponse])
async def revoke_server_invite(
    server_id: uuid.UUID,
    invite_id: uuid.UUID,
    request: ServerInviteRevokeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.revoke_invite(
        db,
        current_user,
        server_id,
        invite_id,
        request,
    )
    return Response.success(
        data=result,
        message="Server invite revoked successfully",
    )


@accept_router.post("/accept", response_model=ResponseSchema[ServerMemberResponse])
async def accept_server_invite(
    request: ServerInviteAcceptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.accept_invite(db, current_user, request)
    return Response.success(
        data=result,
        message="Server invite accepted successfully",
    )
