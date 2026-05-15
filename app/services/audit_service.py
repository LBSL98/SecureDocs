from sqlalchemy.orm import Session

from app.models import AuditLog


def create_audit_log(
    db: Session,
    *,
    action: str,
    outcome: str,
    actor_user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def list_audit_logs(db: Session, limit: int = 100) -> list[AuditLog]:
    safe_limit = max(1, min(limit, 500))
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(safe_limit).all()
