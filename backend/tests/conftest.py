"""Pytest fixtures for the Clarity backend.

Uses a fresh in-memory SQLite DB per test (StaticPool keeps the in-memory DB
shared across the connection pool). This bypasses Alembic — `Base.metadata.create_all`
is enough since SQLAlchemy already encodes the schema in the model classes.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

# Set required env vars BEFORE importing app modules (Settings reads at import time).
os.environ.setdefault(
    "DATABASE_URL", "sqlite+pysqlite:///:memory:"
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")

# Make `app` importable when running pytest from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    TestSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine, monkeypatch) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with the per-test SQLite engine wired in.

    We monkey-patch `app.core.database.SessionLocal` so the lifespan handler
    (which builds its own session via the global factory) also hits the test
    DB instead of the production-configured one.
    """
    TestSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    import app.core.database as core_db
    import app.main as core_main
    monkeypatch.setattr(core_db, "SessionLocal", TestSession, raising=True)
    monkeypatch.setattr(core_main, "SessionLocal", TestSession, raising=True)

    def _get_db_override():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---- Auth helpers --------------------------------------------------------

def _register_and_login(client: TestClient, email: str, username: str, password: str = "password123") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert r.status_code == 201, r.text
    user = r.json()
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def alice(client: TestClient) -> dict:
    return _register_and_login(client, "alice@example.com", "alice")


@pytest.fixture
def bob(client: TestClient) -> dict:
    return _register_and_login(client, "bob@example.com", "bob")


@pytest.fixture
def project(client: TestClient, alice: dict) -> dict:
    r = client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "A project for tests"},
        headers=alice["headers"],
    )
    assert r.status_code == 201, r.text
    return r.json()
