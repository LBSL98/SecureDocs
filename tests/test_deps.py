import pytest
from fastapi import HTTPException

from app.deps import require_authenticated_user, require_role
from app.models import User


def make_user(role: str = "usuario") -> User:
    return User(
        id=1,
        email="user@securedocs.local",
        name="User",
        password_hash="hash",
        role=role,
        is_active=True,
    )


def test_require_authenticated_user_accepts_user():
    user = make_user()

    assert require_authenticated_user(user) is user


def test_require_authenticated_user_rejects_none():
    with pytest.raises(HTTPException) as exc:
        require_authenticated_user(None)

    assert exc.value.status_code == 401


def test_require_role_accepts_allowed_role():
    dependency = require_role("admin", "auditor")
    user = make_user(role="admin")

    assert dependency(user) is user


def test_require_role_rejects_disallowed_role():
    dependency = require_role("admin")
    user = make_user(role="usuario")

    with pytest.raises(HTTPException) as exc:
        dependency(user)

    assert exc.value.status_code == 403
