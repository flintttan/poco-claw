"""ImBindingService - business logic for managing IM identity bindings.

The service owns:

- minting short-lived, single-use binding codes that bridge web OAuth
  to IM linking
- listing and deleting ``ImBinding`` rows for the calling user

Storage lives in :mod:`app.repositories.im`. This service is the
single source of truth for ``im_bindings`` mutations from the web API.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors.exceptions import AppException
from app.core.errors.error_codes import ErrorCode
from app.repositories.im import (
    ImBindingCodeRepository,
    ImBindingRepository,
)
from app.services.provider_validation import assert_known_provider

# 8 chars × 5 bits/char = 40 bits of entropy from Crockford base32.
_BINDING_CODE_LENGTH = 8
_BINDING_CODE_TTL_SECONDS = 600  # 10 minutes


def _generate_binding_code() -> str:
    """Cryptographically-random 8-char Crockford base32 code.

    Crockford base32 omits I/L/O/U to avoid visual ambiguity when the
    user reads or types the code back into the IM chat.
    """
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(_BINDING_CODE_LENGTH))


class ImBindingService:
    """User-facing IM binding operations."""

    def mint_code(
        self,
        db: Session,
        *,
        user_id: str,
        provider: str | None = None,
    ) -> dict:
        """Mint a fresh binding code for ``user_id``.

        ``provider`` is optional scoping: when set, only messages from
        that provider can consume the code (e.g. the UI offers
        "Generate Feishu bind code" and the user is told to paste it
        in their Feishu chat only).
        """
        if provider is not None and provider.strip():
            # ``assert_known_provider`` raises AppException for any
            # value outside the known IM provider whitelist. The Pydantic
            # schema already validates this at the API boundary, but
            # this is defense-in-depth: any internal caller that ends
            # up here via a future code path is also protected.
            clean_provider = assert_known_provider(provider)
        else:
            clean_provider = None
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=_BINDING_CODE_TTL_SECONDS)
        # Generate, persist, and retry on the (vanishingly rare) UNIQUE
        # collision. The Crockford alphabet at length 8 gives ~32^8
        # ≈ 1.1T codes, so collisions are astronomically unlikely, but
        # the loop keeps the surface area tight.
        for _ in range(5):
            code = _generate_binding_code()
            try:
                row = ImBindingCodeRepository.create(
                    db,
                    user_id=user_id,
                    code=code,
                    expires_at=expires_at,
                    provider=clean_provider,
                )
                db.flush()
                return {
                    "code": row.code,
                    "provider": row.provider,
                    "expires_at": row.expires_at.isoformat(),
                    "ttl_seconds": _BINDING_CODE_TTL_SECONDS,
                }
            except Exception:
                db.rollback()
                continue
        raise AppException(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Failed to mint a unique binding code, please retry",
        )

    def list_bindings(self, db: Session, *, user_id: str) -> list[dict]:
        rows = ImBindingRepository.list_for_user(db, user_id=user_id)
        return [
            {
                "id": row.id,
                "provider": row.provider,
                "im_user_id": row.im_user_id,
                "im_union_id": row.im_union_id,
                "im_display_name": row.im_display_name,
                "bound_via": row.bound_via,
                "bound_at": row.bound_at.isoformat() if row.bound_at else None,
                "last_seen_at": row.last_seen_at.isoformat()
                if row.last_seen_at
                else None,
            }
            for row in rows
        ]

    def delete_binding(
        self,
        db: Session,
        *,
        user_id: str,
        binding_id: int,
    ) -> None:
        binding = ImBindingRepository.get_by_id(db, binding_id)
        if binding is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Binding not found",
            )
        if binding.user_id != user_id:
            # Refuse to disclose existence of someone else's binding.
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cannot delete another user's binding",
            )
        ImBindingRepository.delete(db, binding)
        db.flush()


__all__ = [
    "ImBindingService",
    "_generate_binding_code",
]
