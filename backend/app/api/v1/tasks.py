from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.task import TaskEnqueueRequest, TaskEnqueueResponse
from app.services.executor_manager_notify_service import ExecutorManagerNotifyService
from app.services.session_title_service import SessionTitleService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

task_service = TaskService()
title_service = SessionTitleService()
notify_service = ExecutorManagerNotifyService()


@router.post("", response_model=ResponseSchema[TaskEnqueueResponse])
async def enqueue_task(
    request: TaskEnqueueRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Enqueue a task (agent run) for execution."""
    result = task_service.enqueue_task(db, user_id, request)
    if (
        result.accepted_type == "run"
        and result.run_id is not None
        and request.schedule_mode == "immediate"
        and request.scheduled_at is None
    ):
        background_tasks.add_task(
            notify_service.notify_run_enqueued,
            run_id=result.run_id,
            schedule_mode=request.schedule_mode,
            session_id=result.session_id,
        )
    if request.session_id is None:
        background_tasks.add_task(
            title_service.generate_and_update, result.session_id, request.prompt
        )
    return Response.success(data=result, message="Task enqueued successfully")
