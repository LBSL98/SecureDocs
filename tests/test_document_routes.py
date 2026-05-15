from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Document, User
from app.routes import documents as documents_routes
from app.security.crypto import generate_document_crypto_key
from app.security.passwords import hash_password
from app.security.sessions import create_session_token
from app.services.document_service import create_encrypted_document


@pytest.fixture()
def client_and_db(
    tmp_path,
) -> Generator[tuple[TestClient, sessionmaker[Session], dict[str, User]], None, None]:
    database_path = tmp_path / "test_document_routes.db"
    storage_dir = tmp_path / "private_storage"
    crypto_key = generate_document_crypto_key()

    documents_routes.settings.private_storage_dir = str(storage_dir)
    documents_routes.settings.document_crypto_key = crypto_key

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
        owner = User(
            email="owner@securedocs.local",
            name="Owner",
            role="usuario",
            password_hash=hash_password("Owner123!"),
            is_active=True,
        )
        other = User(
            email="other@securedocs.local",
            name="Other",
            role="usuario",
            password_hash=hash_password("Other123!"),
            is_active=True,
        )
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
        db.add_all([owner, other, admin, auditor])
        db.commit()
        db.refresh(owner)
        db.refresh(other)
        db.refresh(admin)
        db.refresh(auditor)

    try:
        yield TestClient(app), testing_session, {
            "owner": owner,
            "other": other,
            "admin": admin,
            "auditor": auditor,
        }
    finally:
        app.dependency_overrides.clear()


def authenticate(client: TestClient, user: User) -> None:
    settings = get_settings()
    client.cookies.set(settings.session_cookie_name, create_session_token(user.id))


def test_upload_document_stores_ciphertext_and_logs_event(client_and_db):
    client, testing_session, users = client_and_db
    authenticate(client, users["owner"])

    response = client.post(
        "/documents",
        files={"upload": ("segredo.txt", b"conteudo sigiloso", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "segredo.txt"

    with testing_session() as db:
        document = db.query(Document).one()
        event = db.query(AuditLog).filter(AuditLog.action == "document_upload").one()
        stored_path = documents_routes.settings.private_storage_dir + "/" + document.stored_filename

    with open(stored_path, "rb") as file:
        stored_bytes = file.read()

    assert b"conteudo sigiloso" not in stored_bytes
    assert event.outcome == "success"


def test_list_documents_returns_only_readable_documents(client_and_db):
    client, testing_session, users = client_and_db
    key = documents_routes.settings.document_crypto_key
    storage_dir = documents_routes.settings.private_storage_dir

    with testing_session() as db:
        create_encrypted_document(
            db,
            owner=users["owner"],
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=storage_dir,
            document_crypto_key=key,
        )

    authenticate(client, users["other"])

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []


def test_owner_can_download_document(client_and_db):
    client, testing_session, users = client_and_db
    key = documents_routes.settings.document_crypto_key
    storage_dir = documents_routes.settings.private_storage_dir

    with testing_session() as db:
        document = create_encrypted_document(
            db,
            owner=users["owner"],
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=storage_dir,
            document_crypto_key=key,
        )

    authenticate(client, users["owner"])

    response = client.get("/documents/" + str(document.id) + "/download")

    assert response.status_code == 200
    assert response.content == b"segredo"
    assert response.headers["content-type"].startswith("text/plain")


def test_user_without_permission_cannot_download_document_and_denial_is_logged(client_and_db):
    client, testing_session, users = client_and_db
    key = documents_routes.settings.document_crypto_key
    storage_dir = documents_routes.settings.private_storage_dir

    with testing_session() as db:
        document = create_encrypted_document(
            db,
            owner=users["owner"],
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=storage_dir,
            document_crypto_key=key,
        )

    authenticate(client, users["other"])

    response = client.get("/documents/" + str(document.id) + "/download")

    assert response.status_code == 403

    with testing_session() as db:
        event = db.query(AuditLog).filter(AuditLog.action == "document_download").one()

    assert event.outcome == "denied"
    assert event.details == "read permission denied"


def test_admin_can_download_any_document(client_and_db):
    client, testing_session, users = client_and_db
    key = documents_routes.settings.document_crypto_key
    storage_dir = documents_routes.settings.private_storage_dir

    with testing_session() as db:
        document = create_encrypted_document(
            db,
            owner=users["owner"],
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=storage_dir,
            document_crypto_key=key,
        )

    authenticate(client, users["admin"])

    response = client.get("/documents/" + str(document.id) + "/download")

    assert response.status_code == 200
    assert response.content == b"segredo"


def test_auditor_cannot_upload_document(client_and_db):
    client, testing_session, users = client_and_db
    authenticate(client, users["auditor"])

    response = client.post(
        "/documents",
        files={"upload": ("segredo.txt", b"conteudo sigiloso", "text/plain")},
    )

    assert response.status_code == 403

    with testing_session() as db:
        assert db.query(Document).count() == 0
