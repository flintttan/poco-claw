import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import task_router
from app.core.client_pool import get_claude_sdk_client_pool
from app.core.middleware import setup_middleware
from app.core.observability.logging import configure_logging

configure_logging(
    debug=os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "y", "on"},
    service_name="executor",
)

app = FastAPI()

setup_middleware(app)
app.include_router(task_router)


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


@app.on_event("shutdown")
async def shutdown_sdk_client_pool() -> None:
    await get_claude_sdk_client_pool().close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
