"""Shared test utilities for IM-message tests.

Test isolation matters here because the inbound-message path uses a
``ContextVar`` to carry the most recent sender ids from
``InboundMessageService.handle_message`` to the command handlers
(``/bind`` and ``/unbind`` need the open_id / union_id of the
sender, and the message is not threaded through the command
dispatcher). If a test leaves a value in the ContextVar, the next
test on the same task can read it and silently pass with the wrong
sender.

``_InboundSenderContextResetMixin`` resets the context to
``(None, None)`` in both ``setUp`` and ``tearDown`` so a
mid-test failure cannot leak state. Subclasses that need a fixture
value should call ``super().setUp()`` first and then call
``_set_inbound_sender_context(...)`` themselves.
"""

from __future__ import annotations

from app.services.im import _set_inbound_sender_context


class _InboundSenderContextResetMixin:
    """Resets the inbound-sender ContextVar around every test.

    ``unittest.IsolatedAsyncioTestCase`` does not isolate the
    ContextVar by default, so we do it explicitly. Without this, a
    flaky test that fails to clean up can poison every subsequent
    test on the same worker.
    """

    def _reset_sender_context(self) -> None:
        _set_inbound_sender_context(sender_open_id=None, sender_union_id=None)

    def setUp(self) -> None:  # type: ignore[override]
        self._reset_sender_context()

    def tearDown(self) -> None:  # type: ignore[override]
        self._reset_sender_context()
