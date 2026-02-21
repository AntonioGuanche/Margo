"""Margó API — FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers.auth import router as auth_router
from app.routers.ingredients import router as ingredients_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: verify DB connection. Shutdown: dispose engine."""
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title="Margó API",
    description="Food cost management for Belgian restaurants",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS ---
allowed_origins: list[str] = [settings.frontend_url]
if settings.environment == "development":
    allowed_origins += [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(ingredients_router, prefix="/api/ingredients", tags=["ingredients"])


# --- Health check ---
class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        version=app.version,
    )
