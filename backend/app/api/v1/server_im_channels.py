"""Server-scoped IM channel endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.im_binding import ServerImChannelResponse, ServerImChannelUpdateRequest
from app.schemas.response import Response, ResponseSchema
from app.services.server_im_channel_service import ServerImChannelService

router = APIRouter(prefix="/servers", tags=["servers"])
service = ServerImChannelService()


@router.get(
    "/{server_id}/im-channels",
    response_model=ResponseSchema[list[ServerImChannelResponse]],
)
async def list_server_im_channels(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    rows = service.list_channels(db, current_user, server_id)
    return Response.success(data=rows, message="Server IM channels retrieved")


@router.patch(
    "/{server_id}/im-channels/{channel_id}",
    response_model=ResponseSchema[ServerImChannelResponse],
)
async def update_server_im_channel(
    server_id: uuid.UUID,
    channel_id: int,
    request: ServerImChannelUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    row = service.update_channel(
        db,
        current_user,
        server_id,
        channel_id,
        request,
    )
    return Response.success(data=row, message="Server IM channel updated")


@router.delete(
    "/{server_id}/im-channels/{channel_id}",
    response_model=ResponseSchema[dict[str, int]],
)
async def unbind_server_im_channel(
    server_id: uuid.UUID,
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.unbind_channel(db, current_user, server_id, channel_id)
    return Response.success(
        data={"channel_id": channel_id},
        message="Server IM channel unbound",
    )
