import unittest

from app.core.engine import AgentExecutor


class AgentExecutorResponseLoopTests(unittest.TestCase):
    def test_result_message_marks_response_stream_terminal(self) -> None:
        result_message_type = type("ResultMessage", (), {})
        message = result_message_type()

        self.assertTrue(AgentExecutor._is_terminal_response_message(message))

    def test_assistant_message_does_not_mark_response_stream_terminal(self) -> None:
        assistant_message_type = type("AssistantMessage", (), {})
        message = assistant_message_type()

        self.assertFalse(AgentExecutor._is_terminal_response_message(message))


if __name__ == "__main__":
    unittest.main()
