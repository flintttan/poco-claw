"""Web endpoints for managing the calling user's IM identity bindings.

Mounted at ``/api/v1/me/bindings`` and ``/api/v1/me/binding-codes``.
These power the Web Settings → Connected Accounts page and the
``/bind <code>`` flow inside IM chats.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.im_binding import (
    BindingCodeCreateRequest,
    BindingCodeResponse,
    ImBindingResponse,
)
from app.schemas.response import Response
from app.services.im_binding_service import ImBindingService

router = APIRouter()


@router.post("/me/binding-codes", response_model=BindingCodeResponse)
async def create_binding_code(
    request: BindingCodeCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Mint a single-use binding code for the calling user.

    The user pastes the code into an IM chat (``/bind <code>``) to
    link that IM identity to their Poco account.
    """
    service = ImBindingService()
    result = service.mint_code(db, user_id=user_id, provider=request.provider)
    db.commit()
    return Response.success(
        data=BindingCodeResponse.model_validate(result),
        message="Binding code generated",
    )


@router.get("/me/bindings", response_model=list[ImBindingResponse])
async def list_my_bindings(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List the calling user's IM identity bindings."""
    service = ImBindingService()
    rows = service.list_bindings(db, user_id=user_id)
    return Response.success(
        data=[ImBindingResponse.model_validate(row) for row in rows],
    )


@router.delete("/me/bindings/{binding_id}")
async def delete_my_binding(
    binding_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Unbind an IM identity from the calling user's account."""
    service = ImBindingService()
    service.delete_binding(db, user_id=user_id, binding_id=binding_id)
    db.commit()
    return Response.success(message="Binding removed")
