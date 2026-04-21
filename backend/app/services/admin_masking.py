from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEYWORDS = (
    "secret",
    "token",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "client_secret",
    "authorization",
)


def _looks_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(keyword in lowered for keyword in SENSITIVE_KEYWORDS)


def _mask_string(value: str) -> str:
    clean = value.strip()
    if not clean:
        return value
    if len(clean) <= 8:
        return "*" * len(clean)
    return f"{clean[:4]}...{clean[-4:]}"


def mask_sensitive_structure(
    value: Any, parent_key: str | None = None
) -> tuple[Any, bool]:
    if isinstance(value, Mapping):
        masked: dict[str, Any] = {}
        contains_sensitive = False
        for key, item in value.items():
            child_parent = str(key)
            child_masked, child_sensitive = mask_sensitive_structure(item, child_parent)
            masked[str(key)] = child_masked
            contains_sensitive = contains_sensitive or child_sensitive
        return masked, contains_sensitive

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        masked_items: list[Any] = []
        contains_sensitive = False
        for item in value:
            child_masked, child_sensitive = mask_sensitive_structure(item, parent_key)
            masked_items.append(child_masked)
            contains_sensitive = contains_sensitive or child_sensitive
        return masked_items, contains_sensitive

    if isinstance(value, str) and parent_key and _looks_sensitive_key(parent_key):
        return _mask_string(value), True

    return value, False
