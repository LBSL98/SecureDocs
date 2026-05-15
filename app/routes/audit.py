from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import DB_DEPENDENCY, require_role
from app.models import User
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])

AUDIT_READER_DEPENDENCY = Depends(require_role("admin", "auditor"))


@router.get("/logs")
def get_audit_logs(
    limit: int = 100,
    current_user: User = AUDIT_READER_DEPENDENCY,
    db: Session = DB_DEPENDENCY,
) -> list[dict[str, int | str | None]]:
    logs = list_audit_logs(db, limit=limit)

    return [
        {
            "id": log.id,
            "actor_user_id": log.actor_user_id,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "outcome": log.outcome,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
