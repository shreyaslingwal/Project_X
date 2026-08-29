"""FastAPI application factory with CORS, lifespan, and route registration.

"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from project_x.api.routes import router
from project_x.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup and shutdown lifecycle hooks.

    On startup: ensures data directories exist and logs configuration.
    On shutdown: placeholder for future cleanup (e.g. persisting state).
    """
    settings.ensure_directories()
    logger.info("Starting %s", settings.APP_NAME)
    logger.info("Generator model: %s", settings.OLLAMA_MODEL)
    logger.info("Rewriter model: %s", settings.REWRITE_MODEL)
    logger.info("Embedding model: %s", settings.EMBEDDING_MODEL)
    logger.info("Upload directory: %s", settings.UPLOAD_DIR.resolve())
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description="Local NotebookLM-style RAG with streaming generation and verifiable citations.",
        version="0.6.0",
        lifespan=lifespan,
    )

    # CORS middleware for local frontend development
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    application.include_router(router)

    # Mount built React frontend if available (e.g. for standalone single-port deployment)
    dist_dir = settings.BASE_DIR / "frontend-react" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        application.mount(
            "/assets",
            StaticFiles(directory=str(dist_dir / "assets")),
            name="assets",
        )

        @application.get("/", include_in_schema=False)
        async def serve_root(request: Request):
            accept = request.headers.get("accept", "")
            if "application/json" in accept and "text/html" not in accept:
                return {
                    "app": settings.APP_NAME,
                    "status": "running",
                    "docs": "/docs",
                }
            return FileResponse(str(dist_dir / "index.html"))
    else:
        @application.get("/")
        async def root():
            return {
                "app": settings.APP_NAME,
                "status": "running",
                "docs": "/docs",
            }

    return application


app = create_app()
