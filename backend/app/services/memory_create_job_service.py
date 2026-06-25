import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.memory_create_job import MemoryCreateJob
from app.repositories.memory_create_job_repository import MemoryCreateJobRepository
from app.schemas.memory import (
    MemoryCreateJobEnqueueResponse,
    MemoryCreateJobResponse,
    MemoryCreateRequest,
)
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class MemoryCreateJobService:
    def __init__(self, memory_service: MemoryService | None = None) -> None:
        self.memory_service = memory_service or MemoryService()

    def enqueue_create(
        self,
        db: Session,
        *,
        user_id: str,
        request: MemoryCreateRequest,
        memory_scope: str | None = None,
        memory_server_id: uuid.UUID | None = None,
    ) -> MemoryCreateJobEnqueueResponse:
        messages: list[dict[str, Any]] = [
            message.model_dump(mode="json") for message in request.messages
        ]
        metadata: dict[str, Any] | None = (
            request.metadata.copy() if request.metadata is not None else None
        )
        # Persist the scope on the metadata so the background worker
        # passes it through when calling the memory backend.
        if memory_scope and memory_scope != "user":
            metadata = dict(metadata or {})
            metadata.setdefault("memory_scope", memory_scope)
            if memory_server_id is not None:
                metadata.setdefault("memory_server_id", str(memory_server_id))
        job = MemoryCreateJobRepository.create(
            db,
            user_id=user_id,
            messages=messages,
            run_id=request.run_id,
            metadata=metadata,
        )
        db.commit()
        db.refresh(job)
        return MemoryCreateJobEnqueueResponse(job_id=job.id, status=job.status)

    def get_job(
        self,
        db: Session,
        *,
        user_id: str,
        job_id: uuid.UUID,
    ) -> MemoryCreateJobResponse:
        job = MemoryCreateJobRepository.get_by_id(db, job_id)
        if job is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Memory create job not found",
            )
        if job.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Memory create job does not belong to the user",
            )
        return self._to_schema(job)

    def get_active_job(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> MemoryCreateJobResponse | None:
        job = MemoryCreateJobRepository.get_latest_active_by_user(
            db,
            user_id=user_id,
        )
        if job is None:
            return None
        return self._to_schema(job)

    def process_create_job(self, job_id: uuid.UUID) -> None:
        db = SessionLocal()
        job: MemoryCreateJob | None = None
        try:
            job = MemoryCreateJobRepository.get_by_id(db, job_id)
            if job is None:
                return
            if job.status not in {"queued", "running"}:
                return

            job.status = "running"
            job.progress = 0
            job.started_at = datetime.now(timezone.utc)
            job.error = None
            db.commit()

            # Pull the scope out of the metadata dict that
            # enqueue_create() put there. The memory service needs
            # these as first-class fields to do the right thing in
            # mem0 (otherwise server-scope writes silently degrade
            # to user-scope).
            memory_scope: str | None = None
            memory_server_id: uuid.UUID | None = None
            raw_meta = job.request_metadata or {}
            if isinstance(raw_meta, dict):
                raw_scope = raw_meta.get("memory_scope")
                if isinstance(raw_scope, str) and raw_scope in {
                    "user",
                    "server",
                    "both",
                }:
                    memory_scope = raw_scope
                raw_sid = raw_meta.get("memory_server_id")
                if isinstance(raw_sid, str) and raw_sid.strip():
                    try:
                        memory_server_id = uuid.UUID(raw_sid)
                    except ValueError:
                        memory_server_id = None

            request = MemoryCreateRequest(
                messages=job.messages,
                run_id=job.run_id,
                metadata=job.request_metadata,
                memory_scope=memory_scope,
                memory_server_id=memory_server_id,
            )
            result = self.memory_service.create_memories(
                user_id=job.user_id, request=request
            )
            self._mark_success(db, job, result)
        except Exception as exc:
            logger.exception("memory_create_job_failed", extra={"job_id": str(job_id)})
            if job is not None:
                db.rollback()
                self._mark_failed(db, job, str(exc))
        finally:
            db.close()

    @staticmethod
    def _mark_success(
        db: Session,
        job: MemoryCreateJob,
        result: Any,
    ) -> None:
        job.status = "success"
        job.progress = 100
        job.result = jsonable_encoder(result)
        job.error = None
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def _mark_failed(db: Session, job: MemoryCreateJob, error: str) -> None:
        job.status = "failed"
        job.error = error
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def _to_schema(job: MemoryCreateJob) -> MemoryCreateJobResponse:
        return MemoryCreateJobResponse(
            job_id=job.id,
            status=job.status,
            progress=int(job.progress or 0),
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
