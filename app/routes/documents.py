from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import AUTHENTICATED_USER_DEPENDENCY, DB_DEPENDENCY, require_role
from app.models import Document, User
from app.services.audit_service import create_audit_log
from app.services.document_service import (
    create_encrypted_document,
    read_decrypted_document,
    user_can_read_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])

settings = get_settings()
DOCUMENT_FILE = File(...)
DOCUMENT_WRITER_DEPENDENCY = Depends(require_role("admin", "usuario"))


def _request_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _request_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _safe_download_filename(filename: str) -> str:
    return filename.replace('"', "").replace("\\", "")


@router.post("")
def upload_document(
    request: Request,
    upload: UploadFile = DOCUMENT_FILE,
    current_user: User = DOCUMENT_WRITER_DEPENDENCY,
    db: Session = DB_DEPENDENCY,
) -> dict[str, str | int]:
    plaintext = upload.file.read()

    try:
        document = create_encrypted_document(
            db,
            owner=current_user,
            original_filename=upload.filename or "documento.bin",
            content_type=upload.content_type,
            plaintext=plaintext,
            storage_dir=settings.private_storage_dir,
            document_crypto_key=settings.document_crypto_key,
        )
    except ValueError as exc:
        create_audit_log(
            db,
            actor_user_id=current_user.id,
            action="document_upload",
            outcome="failure",
            target_type="document",
            ip_address=_request_ip(request),
            user_agent=_request_user_agent(request),
            details=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document upload",
        ) from exc

    create_audit_log(
        db,
        actor_user_id=current_user.id,
        action="document_upload",
        outcome="success",
        target_type="document",
        target_id=str(document.id),
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        details=document.original_filename,
    )

    return {
        "id": document.id,
        "filename": document.original_filename,
        "size_bytes": document.size_bytes,
    }


@router.get("")
def list_documents(
    current_user: User = AUTHENTICATED_USER_DEPENDENCY,
    db: Session = DB_DEPENDENCY,
) -> list[dict[str, str | int]]:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()

    readable_documents = [
        document
        for document in documents
        if user_can_read_document(db, user=current_user, document=document)
    ]

    return [
        {
            "id": document.id,
            "filename": document.original_filename,
            "size_bytes": document.size_bytes,
            "owner_id": document.owner_id,
        }
        for document in readable_documents
    ]


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    request: Request,
    current_user: User = AUTHENTICATED_USER_DEPENDENCY,
    db: Session = DB_DEPENDENCY,
) -> Response:
    document = db.query(Document).filter(Document.id == document_id).first()

    if document is None:
        create_audit_log(
            db,
            actor_user_id=current_user.id,
            action="document_download",
            outcome="failure",
            target_type="document",
            target_id=str(document_id),
            ip_address=_request_ip(request),
            user_agent=_request_user_agent(request),
            details="document not found",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if not user_can_read_document(db, user=current_user, document=document):
        create_audit_log(
            db,
            actor_user_id=current_user.id,
            action="document_download",
            outcome="denied",
            target_type="document",
            target_id=str(document.id),
            ip_address=_request_ip(request),
            user_agent=_request_user_agent(request),
            details="read permission denied",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    plaintext = read_decrypted_document(
        document=document,
        storage_dir=settings.private_storage_dir,
        document_crypto_key=settings.document_crypto_key,
    )

    create_audit_log(
        db,
        actor_user_id=current_user.id,
        action="document_download",
        outcome="success",
        target_type="document",
        target_id=str(document.id),
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        details=document.original_filename,
    )

    filename = _safe_download_filename(document.original_filename)

    return Response(
        content=plaintext,
        media_type=document.content_type or "application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="' + filename + '"'},
    )
