from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import User
from app.security.passwords import hash_password
from app.services.auth_service import authenticate_user, get_user_by_email, normalize_email


def make_test_db(tmp_path):
    database_path = tmp_path / "test_auth_service.db"
    engine = create_engine(
        "sqlite:///" + str(database_path),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session


def create_user(db: Session, email: str, password: str, role: str = "usuario", active: bool = True):
    user = User(
        email=email,
        name="Test User",
        role=role,
        password_hash=hash_password(password),
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_normalize_email_strips_spaces_and_lowercases():
    assert normalize_email("  USER@SecureDocs.LOCAL  ") == "user@securedocs.local"


def test_get_user_by_email_finds_normalized_email(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        create_user(db, "usuario@securedocs.local", "Usuario123!")
        user = get_user_by_email(db, "  USUARIO@SecureDocs.LOCAL  ")

    assert user is not None
    assert user.email == "usuario@securedocs.local"


def test_authenticate_user_accepts_valid_credentials(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        create_user(db, "usuario@securedocs.local", "Usuario123!")
        user = authenticate_user(db, "usuario@securedocs.local", "Usuario123!")

    assert user is not None
    assert user.email == "usuario@securedocs.local"


def test_authenticate_user_rejects_wrong_password(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        create_user(db, "usuario@securedocs.local", "Usuario123!")
        user = authenticate_user(db, "usuario@securedocs.local", "senha-errada")

    assert user is None


def test_authenticate_user_rejects_unknown_user(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        user = authenticate_user(db, "inexistente@securedocs.local", "Usuario123!")

    assert user is None


def test_authenticate_user_rejects_inactive_user(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        create_user(db, "usuario@securedocs.local", "Usuario123!", active=False)
        user = authenticate_user(db, "usuario@securedocs.local", "Usuario123!")

    assert user is None
