"""Tests for the unified UUID parsing helpers."""

from __future__ import annotations

import unittest
import uuid

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.uuid_parsing import parse_uuid_or_error, try_parse_uuid


class TryParseUuidTests(unittest.TestCase):
    """Cover the lenient parser used by read-only paths."""

    def test_returns_none_for_none(self) -> None:
        self.assertIsNone(try_parse_uuid(None))

    def test_returns_uuid_unchanged(self) -> None:
        u = uuid.uuid4()
        self.assertIs(try_parse_uuid(u), u)

    def test_parses_string_uuid(self) -> None:
        s = "550e8400-e29b-41d4-a716-446655440000"
        self.assertEqual(try_parse_uuid(s), uuid.UUID(s))

    def test_strips_whitespace(self) -> None:
        s = "  550e8400-e29b-41d4-a716-446655440000\n"
        self.assertEqual(try_parse_uuid(s), uuid.UUID(s.strip()))

    def test_returns_none_for_garbage(self) -> None:
        self.assertIsNone(try_parse_uuid("not-a-uuid"))
        self.assertIsNone(try_parse_uuid(""))
        self.assertIsNone(try_parse_uuid("   "))

    def test_returns_none_for_unsupported_type(self) -> None:
        # An object whose ``__str__`` raises should be treated as
        # a failure, not propagated.
        class Bad:
            def __str__(self) -> str:
                raise TypeError("nope")

        self.assertIsNone(try_parse_uuid(Bad()))

    def test_accepts_uuid5(self) -> None:
        # Round-trip a non-UUID4 value to ensure we are not
        # version-restricted.
        u = uuid.uuid5(uuid.NAMESPACE_DNS, "example.com")
        self.assertEqual(try_parse_uuid(str(u)), u)


class ParseUuidOrErrorTests(unittest.TestCase):
    """Cover the strict parser used by command handlers."""

    def test_passes_through_valid_uuid(self) -> None:
        s = "550e8400-e29b-41d4-a716-446655440000"
        self.assertEqual(parse_uuid_or_error(s), uuid.UUID(s))

    def test_rejects_garbage(self) -> None:
        with self.assertRaises(AppException) as cm:
            parse_uuid_or_error("not-a-uuid", field="server_id")
        self.assertEqual(cm.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("server_id", cm.exception.message)
        self.assertIn("not-a-uuid", cm.exception.message)

    def test_rejects_none(self) -> None:
        with self.assertRaises(AppException) as cm:
            parse_uuid_or_error(None, field="channel_id")
        self.assertIn("channel_id", cm.exception.message)

    def test_truncates_oversized_value_in_error(self) -> None:
        huge = "a" * 1024
        with self.assertRaises(AppException) as cm:
            parse_uuid_or_error(huge, field="id")
        # The error message must not contain the entire blob; we
        # truncate to 64 chars + ellipsis.
        self.assertLess(len(cm.exception.message), 200)
        self.assertIn("...", cm.exception.message)

    def test_uses_default_field_name(self) -> None:
        with self.assertRaises(AppException) as cm:
            parse_uuid_or_error("garbage")
        self.assertIn("id", cm.exception.message)


if __name__ == "__main__":
    unittest.main()
