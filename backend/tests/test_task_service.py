import unittest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.schemas.input_file import InputFile
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest
from app.services.task_service import TaskService


class TaskServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TaskService()
        self.db = MagicMock()
        self.user_id = "user-1"

    @patch("app.services.task_service.env_var_service.get_system_env_map")
    @patch.object(TaskService, "_build_user_mcp_server_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_skill_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_plugin_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_subagent_ids_defaults", return_value=[])
    def test_build_config_snapshot_accepts_models_from_system_env_catalog(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        get_system_env_map: MagicMock,
    ) -> None:
        get_system_env_map.return_value = {
            "DEFAULT_MODEL": "minimax-default",
            "MODEL_LIST": "minimax-default,minimax-coder",
        }

        result = self.service._build_config_snapshot(
            self.db,
            self.user_id,
            TaskConfig(model="minimax-coder"),
            base_config={},
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["model"], "minimax-coder")
        self.assertEqual(result["model_provider_id"], "minimax")

    @patch("app.services.task_service.env_var_service.get_system_env_map")
    @patch.object(TaskService, "_build_user_mcp_server_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_skill_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_plugin_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_subagent_ids_defaults", return_value=[])
    def test_build_config_snapshot_normalizes_system_default_model_override(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        get_system_env_map: MagicMock,
    ) -> None:
        get_system_env_map.return_value = {
            "DEFAULT_MODEL": "minimax-default",
            "MODEL_LIST": "minimax-default,minimax-coder",
        }

        result = self.service._build_config_snapshot(
            self.db,
            self.user_id,
            TaskConfig(model="minimax-default"),
            base_config={},
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertNotIn("model", result)
        self.assertNotIn("model_provider_id", result)

    @patch.object(TaskService, "_build_project_input_files")
    @patch.object(TaskService, "_apply_project_repo_defaults")
    @patch.object(TaskService, "_build_config_snapshot")
    @patch("app.services.task_service.SessionQueueService")
    @patch("app.services.task_service.RunRepository.get_blocking_by_session")
    @patch("app.services.task_service.SessionRepository.get_by_id_for_update")
    @patch("app.services.task_service.ProjectRepository.get_by_id")
    def test_follow_up_run_reloads_project_for_project_files(
        self,
        get_project_by_id: MagicMock,
        get_session_by_id_for_update: MagicMock,
        get_blocking_by_session: MagicMock,
        session_queue_service_cls: MagicMock,
        build_config_snapshot: MagicMock,
        apply_project_repo_defaults: MagicMock,
        build_project_input_files: MagicMock,
    ) -> None:
        project_id = uuid4()
        session_id = uuid4()
        project = MagicMock(id=project_id, user_id=self.user_id)
        session = MagicMock(
            id=session_id,
            user_id=self.user_id,
            project_id=project_id,
            kind="chat",
            config_snapshot={},
        )
        run_item = MagicMock(id=uuid4(), status="running")
        run = MagicMock(id=uuid4(), status="running")

        get_project_by_id.return_value = project
        get_session_by_id_for_update.return_value = session
        get_blocking_by_session.return_value = None
        build_config_snapshot.return_value = {}
        apply_project_repo_defaults.side_effect = lambda config, _project: config
        build_project_input_files.return_value = [
            InputFile(
                name="guide.md",
                source="project://guide.md",
                size=12,
                content_type="text/markdown",
            )
        ]

        session_queue_service = session_queue_service_cls.return_value
        session_queue_service.get_existing_enqueue_response.return_value = None
        session_queue_service.materialize_run.return_value = (run_item, run)
        session_queue_service.count_active_items.return_value = 0

        result = self.service.enqueue_task(
            self.db,
            self.user_id,
            TaskEnqueueRequest(prompt="hello", session_id=session_id),
        )

        get_project_by_id.assert_called_once_with(self.db, project_id)
        build_project_input_files.assert_called_once_with(self.db, project)
        self.assertEqual(
            session_queue_service.materialize_run.call_args.kwargs[
                "run_config_snapshot"
            ]["input_files"][0]["name"],
            "guide.md",
        )
        self.assertEqual(result.accepted_type, "run")
        self.assertEqual(result.session_id, session_id)


class TaskServiceSharedSessionTests(unittest.TestCase):
    """B1 fix: ``enqueue_task`` must allow a non-owner to drive a
    session they don't own when the session is bound to a Poco server
    and the caller is an active member of that server. Without
    ``server_acl_check`` + ``shared_server_id``, behavior is identical
    to before (hard reject)."""

    def setUp(self) -> None:
        self.service = TaskService()
        self.db = MagicMock()
        self.user_id = "u-caller"
        self.session_id = uuid4()
        self.server_id = uuid4()
        # The session is owned by user-A, but our caller is user-B.
        self.session_owner = "u-owner"

    def _build_session(self) -> MagicMock:
        session = MagicMock()
        session.id = self.session_id
        session.user_id = self.session_owner
        session.project_id = None
        session.kind = "chat"
        session.status = "idle"
        session.config_snapshot = {}
        return session

    @patch("app.services.task_service.SessionQueueService")
    @patch("app.services.task_service.RunRepository.get_blocking_by_session")
    @patch("app.services.task_service.SessionRepository.get_by_id_for_update")
    def test_server_member_passes_ownership_check(
        self,
        get_session_by_id_for_update: MagicMock,
        get_blocking_by_session: MagicMock,
        session_queue_service_cls: MagicMock,
    ) -> None:
        session = self._build_session()
        get_session_by_id_for_update.return_value = session
        get_blocking_by_session.return_value = None
        session_queue_service = session_queue_service_cls.return_value
        session_queue_service.get_existing_enqueue_response.return_value = None

        run_id = uuid4()
        session_queue_service.materialize_run.return_value = (
            MagicMock(id=uuid4()),
            MagicMock(id=run_id, status="queued"),
        )
        session_queue_service.count_active_items.return_value = 0

        acl_calls: list[tuple[object, str]] = []

        def acl_check(server_id, user_id):
            acl_calls.append((server_id, user_id))
            return user_id == self.user_id

        result = self.service.enqueue_task(
            self.db,
            self.user_id,
            TaskEnqueueRequest(prompt="hi", session_id=self.session_id),
            server_acl_check=acl_check,
            shared_server_id=self.server_id,
        )

        # ACL check must have been consulted.
        self.assertEqual(acl_calls, [(self.server_id, self.user_id)])
        # Materialize should have been called with an audit payload
        # that records who actually triggered the run vs. who owns it.
        materialize_kwargs = session_queue_service.materialize_run.call_args.kwargs
        run_config_snapshot = materialize_kwargs["run_config_snapshot"]
        self.assertEqual(run_config_snapshot["_trigger_user_id"], self.user_id)
        self.assertEqual(
            run_config_snapshot["_session_owner_user_id"], self.session_owner
        )
        self.assertEqual(result.session_id, self.session_id)

    @patch("app.services.task_service.SessionQueueService")
    @patch("app.services.task_service.RunRepository.get_blocking_by_session")
    @patch("app.services.task_service.SessionRepository.get_by_id_for_update")
    def test_non_server_member_blocked(
        self,
        get_session_by_id_for_update: MagicMock,
        get_blocking_by_session: MagicMock,
        session_queue_service_cls: MagicMock,
    ) -> None:
        from app.core.errors.exceptions import AppException

        session = self._build_session()
        get_session_by_id_for_update.return_value = session
        get_blocking_by_session.return_value = None

        def acl_check(server_id, user_id):
            return False  # deny all

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(
                self.db,
                self.user_id,
                TaskEnqueueRequest(prompt="hi", session_id=self.session_id),
                server_acl_check=acl_check,
                shared_server_id=self.server_id,
            )

        self.assertIn("Session does not belong to the user", str(ctx.exception))

    @patch("app.services.task_service.SessionQueueService")
    @patch("app.services.task_service.RunRepository.get_blocking_by_session")
    @patch("app.services.task_service.SessionRepository.get_by_id_for_update")
    def test_no_acl_check_defaults_to_hard_reject(
        self,
        get_session_by_id_for_update: MagicMock,
        get_blocking_by_session: MagicMock,
        session_queue_service_cls: MagicMock,
    ) -> None:
        """Backwards compat: HTTP API path passes neither param, so
        a non-owner driving a foreign session still gets rejected
        (today's behavior must not regress)."""

        from app.core.errors.exceptions import AppException

        session = self._build_session()
        get_session_by_id_for_update.return_value = session
        get_blocking_by_session.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(
                self.db,
                self.user_id,
                TaskEnqueueRequest(prompt="hi", session_id=self.session_id),
                # server_acl_check + shared_server_id are NOT passed
            )

        self.assertIn("Session does not belong to the user", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
