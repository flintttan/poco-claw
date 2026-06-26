"""Tests for the user-id length validator.

The validator guards against oversized values reaching the
``String(255)`` columns on ``users.id``,
``channels.last_bound_by_user_id``, etc. Without it, an oversized
value would surface as an opaque ``value too long`` error from
PostgreSQL on the next ``db.flush()``.
"""

from __future__ import annotations

import unittest

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.user_id_validation import (
    MAX_USER_ID_LENGTH,
    assert_valid_user_id,
)


class AssertValidUserIdTests(unittest.TestCase):
    def test_accepts_uuid(self) -> None:
        # Normal Poco user_id is a UUID4 string (36 chars).
        self.assertEqual(
            assert_valid_user_id("550e8400-e29b-41d4-a716-446655440000"),
            "550e8400-e29b-41d4-a716-446655440000",
        )

    def test_accepts_legacy_id(self) -> None:
        # Legacy / migration IDs ("default", "u-admin") are short.
        self.assertEqual(assert_valid_user_id("default"), "default")
        self.assertEqual(assert_valid_user_id("u-admin"), "u-admin")

    def test_strips_whitespace(self) -> None:
        # Trailing whitespace from a misformatted payload is harmless.
        self.assertEqual(
            assert_valid_user_id("  u-admin  "),
            "u-admin",
        )

    def test_accepts_exactly_max_length(self) -> None:
        # Boundary: 255 chars exactly must be accepted.
        ok = "x" * MAX_USER_ID_LENGTH
        self.assertEqual(assert_valid_user_id(ok), ok)

    def test_rejects_oversized(self) -> None:
        too_long = "x" * (MAX_USER_ID_LENGTH + 1)
        with self.assertRaises(AppException) as cm:
            assert_valid_user_id(too_long)
        self.assertEqual(cm.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn(str(MAX_USER_ID_LENGTH), cm.exception.message)

    def test_rejects_none(self) -> None:
        with self.assertRaises(AppException) as cm:
            assert_valid_user_id(None)
        self.assertEqual(cm.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("required", cm.exception.message.lower())

    def test_rejects_empty(self) -> None:
        with self.assertRaises(AppException):
            assert_valid_user_id("")
        with self.assertRaises(AppException):
            assert_valid_user_id("   ")

    def test_max_length_matches_db_column(self) -> None:
        """The constant must match the ``String(255)`` column width.
        If this test fails, update both ``MAX_USER_ID_LENGTH`` and
        the model definitions in ``app/models/user.py`` and
        ``app/models/im.py``."""
        self.assertEqual(MAX_USER_ID_LENGTH, 255)


if __name__ == "__main__":
    unittest.main()
