from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Document, DocumentPermission, User
from app.security.crypto import decrypt_bytes, encrypt_bytes


def _safe_storage_path(storage_dir: str, stored_filename: str) -> Path:
    base_dir = Path(storage_dir).resolve()
    target_path = (base_dir / stored_filename).resolve()

    if base_dir not in target_path.parents and target_path != base_dir:
        raise ValueError("invalid storage path")

    return target_path


def create_encrypted_document(
    db: Session,
    *,
    owner: User,
    original_filename: str,
    content_type: str | None,
    plaintext: bytes,
    storage_dir: str,
    document_crypto_key: str,
) -> Document:
    if owner.id is None:
        raise ValueError("owner must be persisted before creating documents")

    if not original_filename:
        raise ValueError("original_filename must not be empty")

    ciphertext = encrypt_bytes(plaintext, document_crypto_key)
    stored_filename = str(uuid4()) + ".bin"
    target_path = _safe_storage_path(storage_dir, stored_filename)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(ciphertext)

    document = Document(
        owner_id=owner.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=len(plaintext),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def read_decrypted_document(
    *,
    document: Document,
    storage_dir: str,
    document_crypto_key: str,
) -> bytes:
    source_path = _safe_storage_path(storage_dir, document.stored_filename)
    ciphertext = source_path.read_bytes()
    return decrypt_bytes(ciphertext, document_crypto_key)


def grant_read_permission(db: Session, *, document: Document, user: User) -> DocumentPermission:
    existing = (
        db.query(DocumentPermission)
        .filter(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == user.id,
        )
        .first()
    )

    if existing:
        existing.can_read = True
        db.commit()
        db.refresh(existing)
        return existing

    permission = DocumentPermission(
        document_id=document.id,
        user_id=user.id,
        can_read=True,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


def user_can_read_document(db: Session, *, user: User, document: Document) -> bool:
    if user.role == "admin":
        return True

    if document.owner_id == user.id:
        return True

    permission = (
        db.query(DocumentPermission)
        .filter(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == user.id,
            DocumentPermission.can_read.is_(True),
        )
        .first()
    )

    return permission is not None
