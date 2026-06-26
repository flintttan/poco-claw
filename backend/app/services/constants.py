"""Service-layer constants shared across IM, auth, and binding code paths.

The constants here are intentionally narrow (a frozen set of provider
names, a default TTL, etc.) so that they can be imported from any
module without pulling in a heavier dependency.
"""

from __future__ import annotations

SYSTEM_USER_ID = "__system__"

# Whitelist of accepted IM provider identifiers. Every code path that
# accepts a ``provider`` string from outside the parse functions
# (``parse_feishu_update`` etc., which hardcode the value) must validate
# against this set. Adding a new provider is a one-line change here
# plus a literal widening in the relevant Pydantic schemas
# (``schemas/im_binding.py::BindingCodeCreateRequest``,
# ``schemas/auth.py``). See ``assert_known_provider`` for the helper.
KNOWN_IM_PROVIDERS: frozenset[str] = frozenset({"feishu", "dingtalk", "telegram"})
