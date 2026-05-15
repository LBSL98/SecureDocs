from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, User
from app.security.passwords import hash_password


@pytest.fixture()
def client_and_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    database_path = tmp_path / "test_auth_routes.db"
    engine = create_engine(
        "sqlite:///" + str(database_path),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with testing_session() as db:
        user = User(
            email="usuario@securedocs.local",
            name="Usuario Demo",
            role="usuario",
            password_hash=hash_password("Usuario123!"),
            is_active=True,
        )
        db.add(user)
        db.commit()

    try:
        yield TestClient(app), testing_session
    finally:
        app.dependency_overrides.clear()


def test_login_success_sets_httponly_session_cookie(client_and_db):
    client, testing_session = client_and_db
    settings = get_settings()

    response = client.post(
        "/login",
        data={"email": "usuario@securedocs.local", "password": "Usuario123!"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "role": "usuario"}

    set_cookie = response.headers["set-cookie"]
    assert settings.session_cookie_name in set_cookie
    assert "HttpOnly" in set_cookie

    with testing_session() as db:
        events = db.query(AuditLog).filter(AuditLog.action == "login").all()

    assert len(events) == 1
    assert events[0].outcome == "success"


def test_login_failure_returns_401_and_logs_event(client_and_db):
    client, testing_session = client_and_db

    response = client.post(
        "/login",
        data={"email": "usuario@securedocs.local", "password": "senha-errada"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    with testing_session() as db:
        events = db.query(AuditLog).filter(AuditLog.action == "login").all()

    assert len(events) == 1
    assert events[0].outcome == "failure"
    assert events[0].details == "invalid credentials"


def test_logout_requires_authenticated_user(client_and_db):
    client, _ = client_and_db

    response = client.post("/logout")

    assert response.status_code == 401


def test_logout_deletes_cookie_and_logs_event(client_and_db):
    client, testing_session = client_and_db
    settings = get_settings()

    login_response = client.post(
        "/login",
        data={"email": "usuario@securedocs.local", "password": "Usuario123!"},
    )
    assert login_response.status_code == 200

    logout_response = client.post("/logout")

    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}
    assert settings.session_cookie_name in logout_response.headers["set-cookie"]

    with testing_session() as db:
        events = db.query(AuditLog).order_by(AuditLog.id).all()

    assert [event.action for event in events] == ["login", "logout"]
    assert events[-1].outcome == "success"
