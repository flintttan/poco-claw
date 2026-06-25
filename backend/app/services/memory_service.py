from inspect import signature
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.memory import MemoryCreateRequest, MemorySearchRequest

try:
    from mem0 import Memory as Mem0Memory
except ImportError:
    Mem0Memory = None

DEFAULT_MEMORY_AGENT_ID = "poco-agent"


def _server_app_id(server_id: Any) -> str:
    """Stable mem0 ``app_id`` for a Poco server's shared memory zone.

    The ``poco-server:`` prefix namespaces the value so we never
    collide with whatever ``app_id`` mem0 may emit on its own, and
    makes it easy to grep / count via mem0's metadata filters.
    """
    return f"poco-server:{server_id}"


class MemoryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._enabled = self.settings.mem0_enabled
        self._custom_config: dict[str, Any] | None = None
        self._instance: Any | None = None
        self._lock = Lock()

    def is_enabled(self) -> bool:
        return self._enabled

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Memory service is disabled. Set MEM0_ENABLED=true first.",
            )

    def _resolve_openai_api_key(self) -> str:
        api_key = (self.settings.openai_api_key or "").strip()
        if not api_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="OPENAI_API_KEY is required for memory service",
            )
        return api_key

    def _resolve_openai_base_url(self) -> str | None:
        value = (self.settings.openai_base_url or "").strip()
        return value or None

    def _build_graph_store(self) -> dict[str, Any]:
        provider = self.settings.mem0_graph_provider.strip().lower()
        if provider == "memgraph":
            return {
                "provider": "memgraph",
                "config": {
                    "url": self.settings.mem0_memgraph_uri,
                    "username": self.settings.mem0_memgraph_username,
                    "password": self.settings.mem0_memgraph_password,
                },
            }
        if provider != "neo4j":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Unsupported graph provider: {self.settings.mem0_graph_provider}",
            )

        return {
            "provider": "neo4j",
            "config": {
                "url": self.settings.mem0_neo4j_uri,
                "username": self.settings.mem0_neo4j_username,
                "password": self.settings.mem0_neo4j_password,
            },
        }

    def _build_default_config(self) -> dict[str, Any]:
        api_key = self._resolve_openai_api_key()
        openai_base_url = self._resolve_openai_base_url()

        llm_config: dict[str, Any] = {
            "api_key": api_key,
            "model": self.settings.mem0_llm_model,
        }
        embedder_config: dict[str, Any] = {
            "api_key": api_key,
            "model": self.settings.mem0_embedder_model,
            "embedding_dims": self.settings.mem0_embedding_dims,
        }
        if openai_base_url is not None:
            llm_config["openai_base_url"] = openai_base_url
            embedder_config["openai_base_url"] = openai_base_url

        return {
            "vector_store": {
                "provider": self.settings.mem0_vector_provider,
                "config": {
                    "host": self.settings.mem0_postgres_host,
                    "port": self.settings.mem0_postgres_port,
                    "dbname": self.settings.mem0_postgres_db,
                    "user": self.settings.mem0_postgres_user,
                    "password": self.settings.mem0_postgres_password,
                    "collection_name": self.settings.mem0_postgres_collection_name,
                    "embedding_model_dims": self.settings.mem0_embedding_dims,
                },
            },
            "graph_store": self._build_graph_store(),
            "llm": {
                "provider": "openai",
                "config": llm_config,
            },
            "embedder": {
                "provider": "openai",
                "config": embedder_config,
            },
            "history_db_path": self.settings.mem0_history_db_path,
        }

    @staticmethod
    def _ensure_history_db_parent(config: dict[str, Any]) -> None:
        history_db_path = config.get("history_db_path")
        if not isinstance(history_db_path, str):
            return

        path = history_db_path.strip()
        if not path:
            return

        Path(path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_openai_config(config: dict[str, Any]) -> None:
        llm = config.get("llm", {})
        if isinstance(llm, dict) and llm.get("provider") == "openai":
            llm_cfg = llm.get("config", {})
            if (
                not isinstance(llm_cfg, dict)
                or not str(llm_cfg.get("api_key", "")).strip()
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="llm.config.api_key is required when llm.provider is openai",
                )

        embedder = config.get("embedder", {})
        if isinstance(embedder, dict) and embedder.get("provider") == "openai":
            embedder_cfg = embedder.get("config", {})
            if (
                not isinstance(embedder_cfg, dict)
                or not str(embedder_cfg.get("api_key", "")).strip()
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="embedder.config.api_key is required when embedder.provider is openai",
                )

    def _create_instance(self, config: dict[str, Any]) -> Any:
        if Mem0Memory is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="mem0ai dependency is missing. Please install mem0ai first.",
            )

        self._validate_openai_config(config)
        self._ensure_history_db_parent(config)
        return Mem0Memory.from_config(config)

    def _get_instance(self) -> Any:
        with self._lock:
            self._ensure_enabled()
            if self._instance is None:
                config = self._custom_config or self._build_default_config()
                self._instance = self._create_instance(config)
            return self._instance

    @staticmethod
    def _build_scope(
        *,
        user_id: str | None,
        run_id: str | None,
        require_identifier: bool = True,
    ) -> dict[str, Any]:
        if require_identifier and not (user_id or run_id):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="At least one identifier is required (user_id, run_id)",
            )

        params: dict[str, Any] = {}
        if user_id:
            params["user_id"] = user_id
        params["agent_id"] = DEFAULT_MEMORY_AGENT_ID
        if run_id:
            params["run_id"] = run_id
        return params

    def configure(
        self,
        *,
        enabled: bool | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            if enabled is not None:
                self._enabled = enabled
            if config is not None:
                self._custom_config = config
            self._instance = None

    def create_memories(self, *, user_id: str, request: MemoryCreateRequest) -> Any:
        messages = [message.model_dump() for message in request.messages]
        scope = (request.memory_scope or "user").strip().lower() or "user"
        server_id = request.memory_server_id

        user_payload = self._build_scope(user_id=user_id, run_id=request.run_id)
        if request.metadata is not None:
            user_payload["metadata"] = dict(request.metadata)

        if scope == "user" or server_id is None:
            # Default path: per-user memory. Mem0 already isolates by
            # user_id at the storage layer.
            return self._get_instance().add(messages=messages, **user_payload)

        if scope == "server":
            # Server-zone write: tag the record with the server's
            # app_id and drop the user_id so the search filter
            # ``{"app_id": "poco-server:<id>"}`` actually matches.
            server_payload = dict(user_payload)
            server_payload.pop("user_id", None)
            server_payload["app_id"] = _server_app_id(server_id)
            return self._get_instance().add(messages=messages, **server_payload)

        # scope == "both": fan out into two writes so a future
        # scope="both" search can OR them back together.
        server_payload = dict(user_payload)
        server_payload.pop("user_id", None)
        server_payload["app_id"] = _server_app_id(server_id)
        user_result = self._get_instance().add(messages=messages, **user_payload)
        server_result = self._get_instance().add(messages=messages, **server_payload)
        return {"user_scope": user_result, "server_scope": server_result}

    def list_memories(
        self,
        *,
        user_id: str,
        run_id: str | None = None,
    ) -> Any:
        params = self._build_scope(
            user_id=user_id,
            run_id=run_id,
        )
        return self._get_instance().get_all(**params)

    def get_memory(self, memory_id: str) -> Any:
        return self._get_instance().get(memory_id)

    def search_memories(
        self,
        *,
        user_id: str,
        request: MemorySearchRequest,
        memory_scope: str | None = None,
        memory_server_id: Any = None,
    ) -> Any:
        scope = (memory_scope or "user").strip().lower() or "user"
        params: dict[str, Any] = self._build_scope(
            user_id=user_id,
            run_id=request.run_id,
        )
        if request.filters is not None:
            params["filters"] = request.filters

        if scope == "user" or memory_server_id is None:
            return self._get_instance().search(query=request.query, **params)

        server_filter = {"app_id": _server_app_id(memory_server_id)}
        if scope == "server":
            # Server-only: drop the user scope so we don't accidentally
            # see per-user memories that don't belong to this server
            # (mem0 AND-combines ``user_id`` with the ``app_id``
            # filter, so leaving user_id set would hide every server
            # memory from this caller).
            params.pop("user_id", None)
            existing = params.get("filters") or {}
            params["filters"] = {**existing, **server_filter}
            return self._get_instance().search(query=request.query, **params)

        # scope == "both": merge user and server zones via OR.
        existing = params.get("filters") or {}
        params["filters"] = {
            **existing,
            "OR": [
                {"user_id": user_id},
                server_filter,
            ],
        }
        return self._get_instance().search(query=request.query, **params)

    def update_memory(self, *, memory_id: str, text: str) -> Any:
        clean_text = text.strip()
        if not clean_text:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="text must be a non-empty string",
            )

        instance = self._get_instance()
        try:
            update_params = signature(instance.update).parameters
        except (TypeError, ValueError):
            return instance.update(memory_id=memory_id, data=clean_text)

        if "text" in update_params:
            return instance.update(memory_id=memory_id, text=clean_text)
        return instance.update(memory_id=memory_id, data=clean_text)

    def get_memory_history(self, *, memory_id: str) -> Any:
        return self._get_instance().history(memory_id=memory_id)

    def delete_memory(self, *, memory_id: str) -> None:
        self._get_instance().delete(memory_id=memory_id)

    def delete_all_memories(
        self,
        *,
        user_id: str,
        run_id: str | None = None,
    ) -> None:
        params = self._build_scope(
            user_id=user_id,
            run_id=run_id,
        )
        self._get_instance().delete_all(**params)

    def reset(self) -> None:
        self._get_instance().reset()
