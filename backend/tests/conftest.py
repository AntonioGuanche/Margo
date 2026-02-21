"""Shared pytest fixtures for all tests."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.restaurant import Restaurant
from app.services.auth import create_access_token


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test.

    Creates a fresh engine per test to avoid asyncpg event-loop conflicts
    on Windows. Uses savepoints so session.commit() in app code doesn't
    break isolation.
    """
    engine = create_async_engine(settings.database_url, echo=False, pool_size=2, max_overflow=0)

    connection = await engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False)

    # Start a SAVEPOINT inside the outer transaction
    nested = await connection.begin_nested()

    # Re-create the savepoint after each commit so subsequent operations work
    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sync_session, trans):
        nonlocal nested
        if connection.closed or not connection.in_transaction():
            return
        if not nested.is_active:
            nested = connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with DB session override for test isolation."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def restaurant(db_session: AsyncSession) -> Restaurant:
    """Create a test restaurant in the DB and return it."""
    resto = Restaurant(name="Test Restaurant", owner_email="test@heymargo.be")
    db_session.add(resto)
    await db_session.flush()
    await db_session.refresh(resto)
    return resto


@pytest.fixture
def auth_headers(restaurant: Restaurant) -> dict[str, str]:
    """Return Authorization headers with a valid JWT for the test restaurant."""
    token = create_access_token(restaurant.id, restaurant.owner_email)
    return {"Authorization": f"Bearer {token}"}
