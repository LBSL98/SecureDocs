from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import DocumentPermission, User
from app.security.crypto import generate_document_crypto_key
from app.security.passwords import hash_password
from app.services.document_service import (
    create_encrypted_document,
    grant_read_permission,
    read_decrypted_document,
    user_can_read_document,
)


def make_test_db(tmp_path):
    database_path = tmp_path / "test_document_service.db"
    engine = create_engine(
        "sqlite:///" + str(database_path),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session


def create_user(db: Session, email: str, role: str = "usuario") -> User:
    user = User(
        email=email,
        name=email,
        role=role,
        password_hash=hash_password("Senha123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_encrypted_document_stores_ciphertext_not_plaintext(tmp_path):
    testing_session = make_test_db(tmp_path)
    storage_dir = tmp_path / "private_storage"
    key = generate_document_crypto_key()
    plaintext = b"conteudo sigiloso do documento"

    with testing_session() as db:
        owner = create_user(db, "owner@securedocs.local")
        document = create_encrypted_document(
            db,
            owner=owner,
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=plaintext,
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )

    stored_path = storage_dir / document.stored_filename
    stored_bytes = stored_path.read_bytes()

    assert stored_path.exists()
    assert stored_bytes != plaintext
    assert plaintext not in stored_bytes
    assert document.original_filename == "segredo.txt"
    assert document.size_bytes == len(plaintext)


def test_read_decrypted_document_restores_plaintext(tmp_path):
    testing_session = make_test_db(tmp_path)
    storage_dir = tmp_path / "private_storage"
    key = generate_document_crypto_key()
    plaintext = b"conteudo sigiloso do documento"

    with testing_session() as db:
        owner = create_user(db, "owner@securedocs.local")
        document = create_encrypted_document(
            db,
            owner=owner,
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=plaintext,
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )
        restored = read_decrypted_document(
            document=document,
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )

    assert restored == plaintext


def test_owner_can_read_own_document(tmp_path):
    testing_session = make_test_db(tmp_path)
    storage_dir = tmp_path / "private_storage"
    key = generate_document_crypto_key()

    with testing_session() as db:
        owner = create_user(db, "owner@securedocs.local")
        document = create_encrypted_document(
            db,
            owner=owner,
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )

        assert user_can_read_document(db, user=owner, document=document) is True


def test_admin_can_read_any_document(tmp_path):
    testing_session = make_test_db(tmp_path)
    storage_dir = tmp_path / "private_storage"
    key = generate_document_crypto_key()

    with testing_session() as db:
        owner = create_user(db, "owner@securedocs.local")
        admin = create_user(db, "admin@securedocs.local", role="admin")
        document = create_encrypted_document(
            db,
            owner=owner,
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )

        assert user_can_read_document(db, user=admin, document=document) is True


def test_user_without_permission_cannot_read_document(tmp_path):
    testing_session = make_test_db(tmp_path)
    storage_dir = tmp_path / "private_storage"
    key = generate_document_crypto_key()

    with testing_session() as db:
        owner = create_user(db, "owner@securedocs.local")
        other = create_user(db, "other@securedocs.local")
        document = create_encrypted_document(
            db,
            owner=owner,
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )

        assert user_can_read_document(db, user=other, document=document) is False


def test_grant_read_permission_allows_user_to_read(tmp_path):
    testing_session = make_test_db(tmp_path)
    storage_dir = tmp_path / "private_storage"
    key = generate_document_crypto_key()

    with testing_session() as db:
        owner = create_user(db, "owner@securedocs.local")
        other = create_user(db, "other@securedocs.local")
        document = create_encrypted_document(
            db,
            owner=owner,
            original_filename="segredo.txt",
            content_type="text/plain",
            plaintext=b"segredo",
            storage_dir=str(storage_dir),
            document_crypto_key=key,
        )

        permission = grant_read_permission(db, document=document, user=other)

        assert permission.can_read is True
        assert user_can_read_document(db, user=other, document=document) is True
        assert db.query(DocumentPermission).count() == 1
