"""
Continuum - Plugin-driven control-plane UI shell.

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from continuum.app.runtime import ContinuumRuntime
from continuum.adapters.web.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - startup and shutdown."""
    # Startup: boot the runtime
    runtime = ContinuumRuntime()
    app.state.runtime = runtime
    await runtime.boot()

    yield

    # Shutdown: stop the runtime
    await runtime.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Continuum",
        description="Plugin-driven control-plane UI shell",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware - strict origin allowlist
    # V1: localhost origins for development
    # Production: configure via environment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:4040",  # Production
            "capacitor://localhost",  # iOS Capacitor
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Mount API routes
    app.include_router(api_router)

    return app


# Application instance
app = create_app()
