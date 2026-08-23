from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.pull_requests import router as pull_requests_router
from app.api.quota import router as quota_router
from app.api.repositories import router as repositories_router
from app.api.verifications import router as verifications_router
from app.api.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} (Environment: {settings.ENVIRONMENT})...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Evidence-Driven Verification Engine for AI-Generated and Modified Code Changes",
        version="0.1.0",
        lifespan=lifespan
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handling
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error processing request to {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."}
        )

    # Register Routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(quota_router)
    app.include_router(repositories_router)
    app.include_router(pull_requests_router)
    app.include_router(verifications_router)
    app.include_router(webhooks_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
