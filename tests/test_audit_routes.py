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
from app.security.sessions import create_session_token


@pytest.fixture()
def client_and_db(
    tmp_path,
) -> Generator[tuple[TestClient, sessionmaker[Session], dict[str, int]], None, None]:
    database_path = tmp_path / "test_audit_routes.db"
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
        admin = User(
            email="admin@securedocs.local",
            name="Admin",
            role="admin",
            password_hash=hash_password("Admin123!"),
            is_active=True,
        )
        auditor = User(
            email="auditor@securedocs.local",
            name="Auditor",
            role="auditor",
            password_hash=hash_password("Auditor123!"),
            is_active=True,
        )
        user = User(
            email="usuario@securedocs.local",
            name="Usuario",
            role="usuario",
            password_hash=hash_password("Usuario123!"),
            is_active=True,
        )
        db.add_all([admin, auditor, user])
        db.commit()
        db.refresh(admin)
        db.refresh(auditor)
        db.refresh(user)

        user_ids = {
            "admin": admin.id,
            "auditor": auditor.id,
            "user": user.id,
        }

        event = AuditLog(
            actor_user_id=user.id,
            action="document_download",
            target_type="document",
            target_id="1",
            outcome="denied",
            details="read permission denied",
        )
        db.add(event)
        db.commit()

    try:
        yield TestClient(app), testing_session, user_ids
    finally:
        app.dependency_overrides.clear()


def authenticate(client: TestClient, user_id: int) -> None:
    settings = get_settings()
    client.cookies.set(settings.session_cookie_name, create_session_token(user_id))


def test_admin_can_list_audit_logs(client_and_db):
    client, _, user_ids = client_and_db
    authenticate(client, user_ids["admin"])

    response = client.get("/audit/logs")

    assert response.status_code == 200
    assert response.json()[0]["action"] == "document_download"
    assert response.json()[0]["outcome"] == "denied"


def test_auditor_can_list_audit_logs(client_and_db):
    client, _, user_ids = client_and_db
    authenticate(client, user_ids["auditor"])

    response = client.get("/audit/logs")

    assert response.status_code == 200
    assert response.json()[0]["details"] == "read permission denied"


def test_regular_user_cannot_list_audit_logs(client_and_db):
    client, _, user_ids = client_and_db
    authenticate(client, user_ids["user"])

    response = client.get("/audit/logs")

    assert response.status_code == 403


def test_unauthenticated_user_cannot_list_audit_logs(client_and_db):
    client, _, _ = client_and_db

    response = client.get("/audit/logs")

    assert response.status_code == 401
