import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.server import (
    ServerCreateRequest,
    ServerOwnershipTransferRequest,
    ServerResponse,
)
from app.services.server_service import ServerService

router = APIRouter(prefix="/servers", tags=["servers"])

service = ServerService()


@router.get("", response_model=ResponseSchema[list[ServerResponse]])
async def list_servers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_servers(db, current_user)
    return Response.success(data=result, message="Servers retrieved successfully")


@router.post("", response_model=ResponseSchema[ServerResponse])
async def create_server(
    request: ServerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_server(db, current_user, request)
    return Response.success(data=result, message="Server created successfully")


@router.post(
    "/{server_id}/ownership-transfer",
    response_model=ResponseSchema[ServerResponse],
)
async def transfer_server_ownership(
    server_id: uuid.UUID,
    request: ServerOwnershipTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.transfer_ownership(db, current_user, server_id, request)
    return Response.success(
        data=result,
        message="Server ownership transferred successfully",
    )


@router.delete("/{server_id}", response_model=ResponseSchema[dict])
async def delete_server(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_server(db, current_user, server_id)
    return Response.success(
        data={"id": server_id},
        message="Server deleted successfully",
    )
