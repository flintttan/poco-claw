import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.server_channel_message_reaction import ServerChannelMessageReaction
from app.models.user import User
from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionOperationResponse,
)
from app.services.server_channel_message_reaction_service import (
    ServerChannelMessageReactionService,
)


class ServerChannelMessageReactionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.server_id = uuid.uuid4()
        self.channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server_id,
            name="general",
            slug="general",
            visibility="public",
            created_by="user-1",
            archived_at=None,
        )
        self.message = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel.id,
            author_user_id="user-1",
            message_type="user",
            content={"text": "hello"},
            text_preview="hello",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_add_user_reaction_is_idempotent_when_existing(self) -> None:
        service = ServerChannelMessageReactionService()
        existing = ServerChannelMessageReaction(
            id=uuid.uuid4(),
            message_id=self.message.id,
            channel_id=self.channel.id,
            emoji="👍",
            actor_type="user",
            actor_user_id=self.user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        operation = ServerChannelMessageReactionOperationResponse(
            action="add_channel_message_reaction",
            message_id=self.message.id,
        )

        with (
            patch.object(
                service._message_service,
                "_require_channel_access",
                return_value=self.channel,
            ),
            patch.object(
                service,
                "_require_message_in_channel",
                return_value=self.message,
            ),
            patch(
                "app.services.server_channel_message_reaction_service.ServerChannelMessageReactionRepository.get_user_reaction",
                return_value=existing,
            ),
            patch(
                "app.services.server_channel_message_reaction_service.ServerChannelMessageReactionRepository.create"
            ) as create_reaction,
            patch.object(service, "_build_operation_response", return_value=operation),
        ):
            result = service.add_user_reaction(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                self.message.id,
                " 👍 ",
            )

        create_reaction.assert_not_called()
        self.db.commit.assert_called_once()
        self.assertEqual(result.action, "add_channel_message_reaction")

    def test_remove_user_reaction_is_noop_when_missing(self) -> None:
        service = ServerChannelMessageReactionService()
        operation = ServerChannelMessageReactionOperationResponse(
            action="remove_channel_message_reaction",
            message_id=self.message.id,
        )

        with (
            patch.object(
                service._message_service,
                "_require_channel_access",
                return_value=self.channel,
            ),
            patch.object(
                service,
                "_require_message_in_channel",
                return_value=self.message,
            ),
            patch(
                "app.services.server_channel_message_reaction_service.ServerChannelMessageReactionRepository.get_user_reaction",
                return_value=None,
            ),
            patch(
                "app.services.server_channel_message_reaction_service.ServerChannelMessageReactionRepository.delete"
            ) as delete_reaction,
            patch.object(service, "_build_operation_response", return_value=operation),
        ):
            result = service.remove_user_reaction(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                self.message.id,
                "✅",
            )

        delete_reaction.assert_not_called()
        self.db.commit.assert_called_once()
        self.assertEqual(result.action, "remove_channel_message_reaction")

    def test_normalize_emoji_rejects_plain_text(self) -> None:
        with self.assertRaises(AppException):
            ServerChannelMessageReactionService.normalize_emoji("shipit")


if __name__ == "__main__":
    unittest.main()
