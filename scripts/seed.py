from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import User
from app.security.passwords import hash_password

USERS = [
    {
        "email": "admin@securedocs.local",
        "name": "Administrador",
        "role": "admin",
        "password": "Admin123!",
    },
    {
        "email": "usuario@securedocs.local",
        "name": "Usuario Demo",
        "role": "usuario",
        "password": "Usuario123!",
    },
    {
        "email": "auditor@securedocs.local",
        "name": "Auditor Demo",
        "role": "auditor",
        "password": "Auditor123!",
    },
]


def seed_users(db: Session) -> None:
    for item in USERS:
        existing = db.query(User).filter(User.email == item["email"]).first()
        if existing:
            print("skipped_existing_user=" + item["email"])
            continue

        user = User(
            email=item["email"],
            name=item["name"],
            role=item["role"],
            password_hash=hash_password(item["password"]),
            is_active=True,
        )
        db.add(user)
        print("created_user=" + item["email"] + " role=" + item["role"])

    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
