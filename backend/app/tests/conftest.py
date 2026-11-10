"""
Shared fixtures for the API tests.

The API tests talk to a REAL Postgres database, set with TEST_DATABASE_URL, e.g.
    postgresql://postgres:postgres@localhost:5432/runsmart_test

Safety: the tests drop and recreate every table in that database, so we refuse
to run unless the database name contains "test". Your real database can never
be touched by accident. If TEST_DATABASE_URL is not set, the API tests are
skipped (the pure unit tests still run).
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.tests.helpers import register

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def engine():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set, skipping tests that need a database")

    database_name = make_url(TEST_DATABASE_URL).database or ""
    if "test" not in database_name:
        pytest.fail(
            f"Refusing to run: TEST_DATABASE_URL points at '{database_name}'. "
            "The database name must contain 'test' because the tests wipe its tables."
        )

    from app.core.database import Base

    # Importing the models registers their tables on Base.metadata
    from app.models import (  # noqa: F401
        ActivityModel,
        ExplanationModel,
        PlanModel,
        SessionModel,
        UserModel,
    )

    test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine):
    """A session on the test database, for arranging and checking data directly."""
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine):
    from app.core.database import get_db
    from app.main import app

    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

    # Every test starts with empty tables
    with engine.begin() as conn:
        conn.execute(
            text(
                'TRUNCATE "WeekExplanation", "TrainingSession", "TrainingPlan", '
                "activity, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def auth(client) -> dict:
    return register(client)


@pytest.fixture
def other_auth(client) -> dict:
    return register(client, email="someone-else@example.com")
