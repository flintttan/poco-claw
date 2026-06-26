"""Tests for the IM provider whitelist validator.

The validator is a defense-in-depth check: Pydantic schemas already
reject unknown providers at the API boundary, but any service that
takes a ``provider`` argument directly (e.g. ``IdentityResolver``,
``ImBindingService.mint_code``) should also reject unknown values
so that internal callers cannot smuggle in garbage.
"""

from __future__ import annotations

import unittest

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.constants import KNOWN_IM_PROVIDERS
from app.services.provider_validation import assert_known_provider


class AssertKnownProviderTests(unittest.TestCase):
    """Cover the public surface of the validator."""

    def test_accepts_each_known_provider(self) -> None:
        for p in KNOWN_IM_PROVIDERS:
            with self.subTest(provider=p):
                self.assertEqual(assert_known_provider(p), p)

    def test_normalises_case_and_whitespace(self) -> None:
        # ``FEISHU `` -> ``feishu`` so callers do not have to repeat
        # the cleanup at every call site.
        self.assertEqual(
            assert_known_provider("  FEISHU  "),
            "feishu",
        )

    def test_rejects_none(self) -> None:
        with self.assertRaises(AppException) as cm:
            assert_known_provider(None)
        self.assertEqual(cm.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("required", cm.exception.message.lower())

    def test_rejects_empty_string(self) -> None:
        with self.assertRaises(AppException):
            assert_known_provider("")
        with self.assertRaises(AppException):
            assert_known_provider("   ")

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaises(AppException) as cm:
            assert_known_provider("slack")
        self.assertEqual(cm.exception.error_code, ErrorCode.BAD_REQUEST)
        # The error message should mention the offending value AND
        # the allowed set so operators can fix the bad input without
        # digging through the codebase.
        self.assertIn("slack", cm.exception.message)
        self.assertIn("feishu", cm.exception.message)
        self.assertIn("dingtalk", cm.exception.message)
        self.assertIn("telegram", cm.exception.message)

    def test_known_providers_is_a_frozenset(self) -> None:
        """The constant must be immutable to prevent accidental
        runtime mutation that would silently widen the whitelist."""
        self.assertIsInstance(KNOWN_IM_PROVIDERS, frozenset)


if __name__ == "__main__":
    unittest.main()
