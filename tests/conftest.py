from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database import get_db
from migration_utils import run_migrations


@pytest.fixture
def engine(tmp_path):
    db_engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    run_migrations(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine):
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db_session = factory()
    yield db_session
    db_session.close()


@pytest.fixture
def client(session):
    main.app.dependency_overrides[get_db] = lambda: session
    test_client = TestClient(main.app, follow_redirects=False)
    yield test_client
    main.app.dependency_overrides.clear()
