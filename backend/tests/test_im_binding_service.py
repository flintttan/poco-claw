"""Unit tests for ImBindingService (web-side binding codes + bindings CRUD)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.repositories.im import (
    ImBindingCodeRepository,
    ImBindingRepository,
)
from app.services.im_binding_service import (
    ImBindingService,
    _generate_binding_code,
)


def _db():
    db = MagicMock()
    db.flush = MagicMock()
    db.rollback = MagicMock()
    db.commit = MagicMock()
    return db


def _binding_row(*, user_id: str = "u-mine", provider: str = "feishu"):
    b = MagicMock()
    b.id = 11
    b.user_id = user_id
    b.provider = provider
    b.im_user_id = "ou-1"
    b.im_union_id = "on-1"
    b.im_display_name = "Alice"
    b.bound_via = "code"
    b.bound_at = MagicMock()
    b.bound_at.isoformat = MagicMock(return_value="2026-06-25T10:00:00+00:00")
    b.last_seen_at = None
    return b


class GenerateBindingCodeTests(unittest.TestCase):
    def test_generates_8_char_uppercase_alnum_no_ambiguous(self) -> None:
        code = _generate_binding_code()
        self.assertEqual(len(code), 8)
        # Crockford base32: no I, L, O, U
        self.assertNotIn("I", code)
        self.assertNotIn("L", code)
        self.assertNotIn("O", code)
        self.assertNotIn("U", code)

    def test_mint_returns_serializable_dict(self) -> None:
        with patch.object(
            ImBindingCodeRepository, "create", return_value=MagicMock()
        ) as create_mock:
            row = create_mock.return_value
            row.code = "ABC12345"
            row.provider = "feishu"
            row.expires_at.isoformat = MagicMock(
                return_value="2026-06-25T10:10:00+00:00"
            )
            result = ImBindingService().mint_code(
                _db(), user_id="u-1", provider="feishu"
            )

        self.assertEqual(result["code"], "ABC12345")
        self.assertEqual(result["provider"], "feishu")
        self.assertEqual(result["ttl_seconds"], 600)
        create_mock.assert_called_once()

    def test_mint_normalizes_provider(self) -> None:
        with patch.object(
            ImBindingCodeRepository, "create", return_value=MagicMock()
        ) as create_mock:
            row = create_mock.return_value
            row.code = "ABC12345"
            row.provider = None
            row.expires_at.isoformat = MagicMock(
                return_value="2026-06-25T10:10:00+00:00"
            )
            ImBindingService().mint_code(_db(), user_id="u-1", provider="  Feishu ")

        self.assertEqual(create_mock.call_args.kwargs["provider"], "feishu")

    def test_mint_retries_on_collision_then_succeeds(self) -> None:
        row = MagicMock()
        row.code = "XYZ12345"
        row.provider = None
        row.expires_at.isoformat = MagicMock(return_value="2026-06-25T10:10:00+00:00")
        side_effects = [Exception("duplicate"), row]

        with patch.object(ImBindingCodeRepository, "create", side_effect=side_effects):
            result = ImBindingService().mint_code(_db(), user_id="u-1")

        self.assertEqual(result["code"], "XYZ12345")


class ListBindingsTests(unittest.TestCase):
    def test_returns_serializable_list(self) -> None:
        with patch.object(
            ImBindingRepository, "list_for_user", return_value=[_binding_row()]
        ):
            result = ImBindingService().list_bindings(_db(), user_id="u-mine")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provider"], "feishu")
        self.assertEqual(result[0]["bound_via"], "code")


class DeleteBindingTests(unittest.TestCase):
    def test_delete_own_binding(self) -> None:
        binding = _binding_row(user_id="u-mine")
        db = _db()
        with (
            patch.object(ImBindingRepository, "get_by_id", return_value=binding),
            patch.object(ImBindingRepository, "delete") as delete_mock,
        ):
            ImBindingService().delete_binding(db, user_id="u-mine", binding_id=11)

        delete_mock.assert_called_once_with(db, binding)

    def test_delete_other_users_binding_is_forbidden(self) -> None:
        from app.core.errors.error_codes import ErrorCode

        with patch.object(
            ImBindingRepository,
            "get_by_id",
            return_value=_binding_row(user_id="u-other"),
        ):
            with self.assertRaises(AppException) as ctx:
                ImBindingService().delete_binding(
                    _db(), user_id="u-mine", binding_id=11
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.FORBIDDEN)

    def test_delete_missing_binding_is_not_found(self) -> None:
        from app.core.errors.error_codes import ErrorCode

        with patch.object(ImBindingRepository, "get_by_id", return_value=None):
            with self.assertRaises(AppException) as ctx:
                ImBindingService().delete_binding(
                    _db(), user_id="u-mine", binding_id=11
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
