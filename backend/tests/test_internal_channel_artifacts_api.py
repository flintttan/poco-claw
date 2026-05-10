import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_db, require_internal_token
from app.main import create_app


class InternalChannelArtifactsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.app.dependency_overrides[get_db] = lambda: object()
        self.app.dependency_overrides[require_internal_token] = lambda: None
        self.session_id = uuid.uuid4()
        self.artifact_id = uuid.uuid4()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.internal_channel_artifacts.service.list_runtime_artifacts")
    def test_list_internal_channel_artifacts_returns_runtime_contract(
        self, list_runtime
    ):
        list_runtime.return_value.model_dump.return_value = {
            "artifacts": [
                {
                    "artifact_id": str(self.artifact_id),
                    "logical_path": "/plans/rate-limit-plan.md",
                    "display_name": "rate-limit-plan.md",
                    "content_kind": "text",
                }
            ]
        }

        response = self.client.get(
            f"/api/v1/internal/channel-artifacts/list?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(
            body["data"]["artifacts"][0]["logical_path"],
            "/plans/rate-limit-plan.md",
        )
        list_runtime.assert_called_once()

    @patch("app.api.v1.internal_channel_artifacts.service.read_runtime_artifact")
    def test_read_internal_channel_artifact_accepts_logical_path(self, read_runtime):
        read_runtime.return_value.model_dump.return_value = {
            "artifact": {
                "artifact_id": str(self.artifact_id),
                "logical_path": "/plans/rate-limit-plan.md",
                "display_name": "rate-limit-plan.md",
                "content_kind": "text",
            },
            "content": "# Plan",
            "truncated": False,
            "metadata_only": False,
        }

        response = self.client.post(
            f"/api/v1/internal/channel-artifacts/read?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
            json={"logical_path": "/plans/rate-limit-plan.md"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["content"], "# Plan")
        read_runtime.assert_called_once()

    @patch("app.api.v1.internal_channel_artifacts.service.search_runtime_artifacts")
    def test_search_internal_channel_artifacts_returns_matches(self, search_runtime):
        search_runtime.return_value.model_dump.return_value = {
            "artifacts": [
                {
                    "artifact_id": str(self.artifact_id),
                    "logical_path": "/plans/rate-limit-plan.md",
                    "display_name": "rate-limit-plan.md",
                    "content_kind": "text",
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/internal/channel-artifacts/search?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
            json={"query": "rate limit"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(len(body["data"]["artifacts"]), 1)
        search_runtime.assert_called_once()


if __name__ == "__main__":
    unittest.main()
