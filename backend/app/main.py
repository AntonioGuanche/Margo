"""Margó API — FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.logging_config import setup_logging
from app.middleware.error_handler import register_error_handlers
from fastapi.staticfiles import StaticFiles

from app.routers.alerts import router as alerts_router
from app.routers.auth import router as auth_router
from app.routers.billing import router as billing_router
from app.routers.export import router as export_router
from app.routers.ingredients import router as ingredients_router
from app.routers.onboarding import router as onboarding_router
from app.routers.invoices import router as invoices_router
from app.routers.recipes import router as recipes_router
from app.routers.restaurants import router as restaurants_router
from app.routers.simulator import router as simulator_router
from app.routers.webhooks import router as webhooks_router

# Setup structured logging before anything else
setup_logging()


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

# --- Global error handlers ---
register_error_handlers(app)

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
app.include_router(recipes_router, prefix="/api/recipes", tags=["recipes"])
app.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
app.include_router(invoices_router, prefix="/api/invoices", tags=["invoices"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])
app.include_router(simulator_router, prefix="/api/recipes", tags=["simulator"])
app.include_router(billing_router, prefix="/api/billing", tags=["billing"])
app.include_router(export_router, prefix="/api/export", tags=["export"])
app.include_router(restaurants_router, prefix="/api/restaurants", tags=["restaurants"])
app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

# --- Static files for uploads (dev only) ---
if settings.environment == "development":
    from pathlib import Path
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


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
