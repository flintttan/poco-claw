import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.schemas.channel_artifact import (
    AgentChannelArtifactReadRequest,
    AgentChannelArtifactSearchRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.channel_artifact_service import ChannelArtifactService

router = APIRouter(prefix="/internal/channel-artifacts", tags=["internal"])
service = ChannelArtifactService()


@router.get("/list", response_model=ResponseSchema[dict])
async def list_channel_artifacts_internal(
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_runtime_artifacts(db, session_id=session_id)
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifacts listed",
    )


@router.post("/read", response_model=ResponseSchema[dict])
async def read_channel_artifact_internal(
    request: AgentChannelArtifactReadRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.read_runtime_artifact(
        db,
        session_id=session_id,
        artifact_id=request.artifact_id,
        logical_path=request.logical_path,
        max_bytes=request.max_bytes,
    )
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifact read",
    )


@router.post("/search", response_model=ResponseSchema[dict])
async def search_channel_artifacts_internal(
    request: AgentChannelArtifactSearchRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.search_runtime_artifacts(
        db,
        session_id=session_id,
        query=request.query,
        limit=request.limit,
        include_content=request.include_content,
    )
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifacts searched",
    )
