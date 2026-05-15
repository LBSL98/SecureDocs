from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import AUTHENTICATED_USER_DEPENDENCY, DB_DEPENDENCY
from app.models import User
from app.security.sessions import create_session_token
from app.services.audit_service import create_audit_log
from app.services.auth_service import authenticate_user, normalize_email

router = APIRouter(tags=["auth"])

settings = get_settings()
EMAIL_FORM = Form(...)
PASSWORD_FORM = Form(...)


def _request_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _request_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/login")
def login(
    request: Request,
    response: Response,
    email: str = EMAIL_FORM,
    password: str = PASSWORD_FORM,
    db: Session = DB_DEPENDENCY,
) -> dict[str, str]:
    normalized_email = normalize_email(email)
    user = authenticate_user(db, normalized_email, password)

    if user is None:
        create_audit_log(
            db,
            action="login",
            outcome="failure",
            target_type="user",
            target_id=normalized_email,
            ip_address=_request_ip(request),
            user_agent=_request_user_agent(request),
            details="invalid credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_session_token(user.id)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    create_audit_log(
        db,
        actor_user_id=user.id,
        action="login",
        outcome="success",
        target_type="user",
        target_id=str(user.id),
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        details="login successful",
    )

    return {"status": "ok", "role": user.role}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = AUTHENTICATED_USER_DEPENDENCY,
    db: Session = DB_DEPENDENCY,
) -> dict[str, str]:
    create_audit_log(
        db,
        actor_user_id=current_user.id,
        action="logout",
        outcome="success",
        target_type="user",
        target_id=str(current_user.id),
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        details="logout successful",
    )

    response.delete_cookie(key=settings.session_cookie_name)

    return {"status": "ok"}
