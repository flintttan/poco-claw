import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.schemas.response import Response, ResponseSchema
from app.schemas.server_channel_task_agent import (
    AgentChannelTaskClaimSelfRequest,
    AgentChannelTaskCommentRequest,
    AgentChannelTaskCreateRequest,
    AgentChannelTaskListRequest,
    AgentChannelTaskReadRequest,
    AgentChannelTaskStatusRequest,
)
from app.services.server_channel_task_agent_service import (
    ServerChannelTaskAgentService,
)

router = APIRouter(prefix="/internal/server-channel-tasks", tags=["internal"])
service = ServerChannelTaskAgentService()


@router.post("/create", response_model=ResponseSchema[Any])
async def create_server_channel_task_internal(
    request: AgentChannelTaskCreateRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_task(db, session_id=session_id, request=request)
    return Response.success(data=result, message="Agent channel task created")


@router.post("/list", response_model=ResponseSchema[Any])
async def list_server_channel_tasks_internal(
    request: AgentChannelTaskListRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_tasks(db, session_id=session_id, request=request)
    return Response.success(data=result, message="Agent channel tasks listed")


@router.post("/read", response_model=ResponseSchema[Any])
async def read_server_channel_task_internal(
    request: AgentChannelTaskReadRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.read_task(db, session_id=session_id, request=request)
    return Response.success(data=result, message="Agent channel task read")


@router.post("/status", response_model=ResponseSchema[Any])
async def update_server_channel_task_status_internal(
    request: AgentChannelTaskStatusRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_task_status(db, session_id=session_id, request=request)
    return Response.success(data=result, message="Agent channel task status updated")


@router.post("/claim", response_model=ResponseSchema[Any])
async def claim_server_channel_task_internal(
    request: AgentChannelTaskClaimSelfRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.claim_task(db, session_id=session_id, request=request)
    return Response.success(data=result, message="Agent channel task claimed")


@router.post("/comment", response_model=ResponseSchema[Any])
async def comment_server_channel_task_internal(
    request: AgentChannelTaskCommentRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.comment_on_task(db, session_id=session_id, request=request)
    return Response.success(data=result, message="Agent channel task commented")
