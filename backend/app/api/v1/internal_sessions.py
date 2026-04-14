import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.internal_session import InternalSessionStatusUpdateRequest
from app.schemas.internal_session import (
    SessionCancellationClaimRequest,
    SessionCancellationClaimResponse,
    SessionCancellationCompleteRequest,
    SessionCancellationCompleteResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.schemas.session import (
    SessionCreateRequest,
    SessionResponse,
    SessionStateResponse,
    SessionUpdateRequest,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/internal/sessions", tags=["internal-sessions"])

session_service = SessionService()


@router.post("", response_model=ResponseSchema[SessionResponse])
async def create_session_internal(
    request: SessionCreateRequest,
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = session_service.create_session(db, user_id, request)
    return Response.success(
        data=SessionResponse.model_validate(db_session),
        message="Session created successfully",
    )


@router.get("/{session_id}", response_model=ResponseSchema[SessionResponse])
async def get_session_internal(
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = session_service.get_session(db, session_id)
    return Response.success(
        data=SessionResponse.model_validate(db_session),
        message="Session retrieved successfully",
    )


@router.get("/{session_id}/state", response_model=ResponseSchema[SessionStateResponse])
async def get_session_state_internal(
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = session_service.get_session(db, session_id)
    return Response.success(
        data=SessionStateResponse.model_validate(db_session),
        message="Session state retrieved successfully",
    )


@router.patch("/{session_id}/status", response_model=ResponseSchema[SessionResponse])
async def update_session_status_internal(
    session_id: uuid.UUID,
    request: InternalSessionStatusUpdateRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = session_service.update_session(
        db,
        session_id,
        SessionUpdateRequest(status=request.status),
    )
    return Response.success(
        data=SessionResponse.model_validate(db_session),
        message="Session updated successfully",
    )


@router.post(
    "/cancellations/claim",
    response_model=ResponseSchema[SessionCancellationClaimResponse | None],
)
async def claim_session_cancellation_internal(
    request: SessionCancellationClaimRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = session_service.claim_next_cancellation(
        db,
        worker_id=request.worker_id,
        lease_seconds=request.lease_seconds,
    )
    return Response.success(
        data=result,
        message="Session cancellation claimed"
        if result
        else "No pending cancellations",
    )


@router.post(
    "/{session_id}/cancellation-complete",
    response_model=ResponseSchema[SessionCancellationCompleteResponse],
)
async def complete_session_cancellation_internal(
    session_id: uuid.UUID,
    request: SessionCancellationCompleteRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = session_service.complete_cancellation(
        db,
        session_id,
        worker_id=request.worker_id,
        stop_status=request.stop_status,
        message=request.message,
    )
    return Response.success(
        data=result,
        message="Session cancellation processed successfully",
    )
