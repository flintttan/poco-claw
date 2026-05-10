from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.response import Response, ResponseSchema
from app.services.backend_client import BackendClient

router = APIRouter(prefix="/agent-channel-artifacts", tags=["agent-channel-artifacts"])
backend_client = BackendClient()


@router.post("/list", response_model=ResponseSchema[Any])
async def list_agent_channel_artifacts(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    result = await backend_client.list_agent_channel_artifacts(session_id)
    return Response.success(data=result, message="Agent channel artifacts listed")


@router.post("/read", response_model=ResponseSchema[Any])
async def read_agent_channel_artifact(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    result = await backend_client.read_agent_channel_artifact(session_id, payload)
    return Response.success(data=result, message="Agent channel artifact read")


@router.post("/search", response_model=ResponseSchema[Any])
async def search_agent_channel_artifacts(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    result = await backend_client.search_agent_channel_artifacts(session_id, payload)
    return Response.success(data=result, message="Agent channel artifacts searched")
