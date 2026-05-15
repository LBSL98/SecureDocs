from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.security.sessions import verify_session_token

settings = get_settings()
SESSION_COOKIE = Cookie(default=None, alias=settings.session_cookie_name)
DB_DEPENDENCY = Depends(get_db)


def get_current_user(
    session_token: str | None = SESSION_COOKIE,
    db: Session = DB_DEPENDENCY,
) -> User | None:
    user_id = verify_session_token(session_token)

    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    return user


CURRENT_USER_DEPENDENCY = Depends(get_current_user)


def require_authenticated_user(
    current_user: User | None = CURRENT_USER_DEPENDENCY,
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return current_user


AUTHENTICATED_USER_DEPENDENCY = Depends(require_authenticated_user)


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    def dependency(
        current_user: User = AUTHENTICATED_USER_DEPENDENCY,
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        return current_user

    return dependency
