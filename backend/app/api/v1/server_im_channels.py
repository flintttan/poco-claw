"""Server-scoped IM channel endpoints.

Mounted at ``/api/v1/servers/{server_id}/im-channels``. The endpoint
returns the list of IM chats currently bound to the server, for the
server-detail page's "Linked IM chats" panel.

Access control: any active member of the server can read the list.
A user who is not a member of the server gets a 403 — the same
shape as the rest of the server API, so the UI can render a single
error path.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.repositories.im import ChannelRepository
from app.repositories.server_member_repository import ServerMemberRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.im_binding import ServerImChannelResponse
from app.schemas.response import Response, ResponseSchema

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get(
    "/{server_id}/im-channels",
    response_model=ResponseSchema[list[ServerImChannelResponse]],
)
async def list_server_im_channels(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List the IM chats currently bound to ``server_id``.

    The caller must be an active member of the server. We do not
    require server admin/owner: every member has a legitimate need
    to know which IM chats are linked (so they can avoid sending
    sensitive content to the wrong group, for example).
    """
    server = ServerRepository.get_by_id(db, server_id)
    if server is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message="Server not found",
        )

    membership = ServerMemberRepository.get_by_server_and_user(
        db, server_id, current_user.id
    )
    if membership is None or membership.status != "active":
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Not a member of this server",
        )

    channels = ChannelRepository.list_by_server(db, server_id=server_id)
    rows = [
        ServerImChannelResponse(
            id=ch.id,
            provider=ch.provider,
            destination=ch.destination,
            chat_type=ch.chat_type,
            enabled=ch.enabled,
            last_bound_by_user_id=ch.last_bound_by_user_id,
            last_bound_at=ch.last_bound_at,
        )
        for ch in channels
    ]
    return Response.success(data=rows, message="Server IM channels retrieved")
