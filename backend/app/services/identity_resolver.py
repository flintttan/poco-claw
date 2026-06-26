"""IdentityResolver - maps an IM sender to a Poco user.

The resolver is the single source of truth for "who is talking to the
bot right now?" in the IM gateway. It is intentionally provider-
agnostic: same code path for Feishu, DingTalk, Telegram, or any
future provider that fills ``InboundMessage.sender_open_id`` /
``sender_union_id``.

Resolution priority
-------------------

1. ``im_bindings`` by ``(provider, im_user_id)`` — the primary path
   for users who have already linked this IM identity to a Poco
   account (either via a binding code or via OAuth auto-bind).
2. ``im_bindings`` by ``(provider, im_union_id)`` — covers IM events
   that carry the union/unionId but not the open/staff id.
3. ``auth_identities`` by ``(provider, provider_user_id)`` — for
   providers that support both OAuth login AND IM (currently just
   Feishu), an existing OAuth identity is an automatic IM binding on
   the next inbound message. The resolver creates an ``im_bindings``
   row on the fly so the next message takes the fast path (1).

The resolver never creates a Poco user. Accounts are created only
through OAuth (web login) or by an admin invitation. IM is a delivery
channel, not an identity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.exceptions import AppException
from app.models.auth_identity import AuthIdentity
from app.repositories.auth_identity_repository import AuthIdentityRepository
from app.repositories.im import ImBindingRepository
from app.services.provider_validation import assert_known_provider

if TYPE_CHECKING:
    from app.models.im import ImBinding

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IdentityResolution:
    user_id: str | None
    # ``bound=True`` means we found a Poco user for this IM identity
    # (via an existing ``im_bindings`` row or via an OAuth auto-bind
    # created during this call). ``bound=False`` means we did not —
    # the caller should ask the user to generate a binding code from
    # the web UI and send it in IM.
    bound: bool
    # When the resolver auto-creates an ``im_bindings`` row from an
    # OAuth identity, this flag is True. The IM command layer uses it
    # to render a one-time notice ("FYI we linked your Feishu login to
    # this chat").
    auto_bound: bool = False
    # Resolution reason for logging / telemetry.
    reason: str = "unknown"


class IdentityResolver:
    """Provider-agnostic IM identity resolver.

    The instance is stateless apart from a logger; every call hits
    the database for the most up-to-date answer. Server restart is
    therefore a no-op for resolution correctness.
    """

    async def resolve(
        self,
        db: Session,
        *,
        provider: str,
        sender_open_id: str | None,
        sender_union_id: str | None,
    ) -> IdentityResolution:
        # ``assert_known_provider`` rejects empty / unknown providers
        # with a 400. InboundMessage.provider is normally a hardcoded
        # constant from the parse functions, but a misconfigured
        # gateway could forward an unknown value; this catches that
        # before we burn a database query.
        try:
            provider = assert_known_provider(provider)
        except AppException:
            return IdentityResolution(user_id=None, bound=False, reason="no_provider")
        sender_open_id = (sender_open_id or "").strip() or None
        sender_union_id = (sender_union_id or "").strip() or None

        if not sender_open_id and not sender_union_id:
            return IdentityResolution(user_id=None, bound=False, reason="no_sender_id")

        # 1) Primary: im_bindings by (provider, im_user_id).
        if sender_open_id:
            binding = ImBindingRepository.get_by_provider_im_user_id(
                db, provider=provider, im_user_id=sender_open_id
            )
            if binding is not None:
                ImBindingRepository.touch_last_seen(db, binding)
                return IdentityResolution(
                    user_id=binding.user_id,
                    bound=True,
                    reason="binding_open_id",
                )

        # 2) Secondary: im_bindings by (provider, im_union_id).
        if sender_union_id and sender_union_id != sender_open_id:
            binding = ImBindingRepository.get_by_provider_im_union_id(
                db, provider=provider, im_union_id=sender_union_id
            )
            if binding is not None:
                ImBindingRepository.touch_last_seen(db, binding)
                return IdentityResolution(
                    user_id=binding.user_id,
                    bound=True,
                    reason="binding_union_id",
                )

        # 3) Auto-bind from OAuth identity (only when this provider
        # supports both OAuth login and IM). Feishu is the only such
        # provider today; DingTalk does not currently expose a public
        # OAuth login flow to the same identity.
        identity = self._lookup_oauth_identity(
            db,
            provider=provider,
            im_user_id=sender_open_id,
            im_union_id=sender_union_id,
        )
        if identity is not None:
            user_id = self._auto_bind_from_oauth(
                db,
                identity=identity,
                provider=provider,
                im_user_id=sender_open_id or identity.provider_user_id,
                im_union_id=sender_union_id,
            )
            if user_id is not None:
                return IdentityResolution(
                    user_id=user_id,
                    bound=True,
                    auto_bound=True,
                    reason="oauth_auto_bind",
                )

        return IdentityResolution(user_id=None, bound=False, reason="needs_bind")

    @staticmethod
    def _lookup_oauth_identity(
        db: Session,
        *,
        provider: str,
        im_user_id: str | None,
        im_union_id: str | None,
    ) -> AuthIdentity | None:
        """Find an auth_identities row that matches this IM identity.

        Tries provider_user_id (= union_id for Feishu) first, then the
        open_id stored in the OAuth profile_json. Skipped entirely for
        providers that don't have a 1:1 OAuth↔IM identity relationship
        to avoid cross-provider pollution.
        """
        # Only attempt auto-bind for providers where OAuth and IM share
        # an identity. Extend this set when DingTalk / WeCom work etc.
        if provider not in {"feishu"}:
            return None

        for pid in (im_union_id, im_user_id):
            if not pid:
                continue
            identity = AuthIdentityRepository.get_by_provider_user_id(db, provider, pid)
            if identity is not None:
                return identity
        return None

    @staticmethod
    def _auto_bind_from_oauth(
        db: Session,
        *,
        identity: AuthIdentity,
        provider: str,
        im_user_id: str,
        im_union_id: str | None,
    ) -> str | None:
        """Create an im_bindings row from a verified OAuth identity.

        Returns the user_id on success, ``None`` if the binding already
        raced ahead of us (handled by the UNIQUE constraint).

        Lookup correctness: the existing-bindings scan checks *both*
        ``(provider, im_user_id)`` and ``(provider, im_union_id)``,
        because a previous binding may have been created from the
        union side of an IM event while the current event carries a
        different open_id. Missing the im_union_id branch lets us
        insert a duplicate row that collides on the unique constraint
        and is then silently discarded, which is exactly the bug the
        OAuth auto-bind path is meant to avoid.
        """
        # If the user is already bound, return that user. This can
        # happen if the same OAuth identity already produced a binding
        # for a different open_id (e.g. Feishu OAuth returns union_id,
        # IM event returns open_id, both should map to the same user).
        for pid in (im_user_id, im_union_id):
            if not pid:
                continue
            existing = ImBindingRepository.get_by_provider_im_user_id(
                db, provider=provider, im_user_id=pid
            )
            if existing is not None:
                if existing.user_id == identity.user_id:
                    return existing.user_id
                # If the binding exists but maps to a different user,
                # do not auto-rebind — that would silently change
                # ownership and the caller must resolve it manually.
                return None
            existing = ImBindingRepository.get_by_provider_im_union_id(
                db, provider=provider, im_union_id=pid
            )
            if existing is not None:
                if existing.user_id == identity.user_id:
                    return existing.user_id
                return None

        binding = ImBindingRepository.create(
            db,
            user_id=identity.user_id,
            provider=provider,
            im_user_id=im_user_id,
            im_union_id=im_union_id,
            bound_via="oauth_auto",
        )
        try:
            with db.begin_nested():
                db.flush([binding])
        except IntegrityError:
            # Concurrent auto-bind won (or a row with the same
            # im_union_id already exists from a different open_id).
            # Re-read by both keys and trust the winner.
            winner: ImBinding | None = None
            for pid in (im_user_id, im_union_id):
                if not pid or winner is not None:
                    continue
                winner = ImBindingRepository.get_by_provider_im_user_id(
                    db, provider=provider, im_user_id=pid
                ) or ImBindingRepository.get_by_provider_im_union_id(
                    db, provider=provider, im_union_id=pid
                )
            if winner is not None and winner.user_id == identity.user_id:
                return winner.user_id
            if winner is not None:
                logger.warning(
                    "im_oauth_auto_bind_conflict",
                    extra={
                        "provider": provider,
                        "im_user_id": im_user_id,
                        "im_union_id": im_union_id,
                        "oauth_user": identity.user_id,
                        "existing_user": winner.user_id,
                    },
                )
            return None
        logger.info(
            "im_oauth_auto_bind_created",
            extra={
                "user_id": identity.user_id,
                "provider": provider,
                "im_user_id": im_user_id,
                "im_union_id": im_union_id,
            },
        )
        return identity.user_id


__all__ = [
    "IdentityResolver",
    "IdentityResolution",
]
