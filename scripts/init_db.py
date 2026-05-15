from app import models
from app.database import Base, engine


def main() -> None:
    registered_models = (
        models.User,
        models.Document,
        models.DocumentPermission,
        models.AuditLog,
    )
    print("registered_models=" + str(len(registered_models)))

    Base.metadata.create_all(bind=engine)
    table_names = sorted(Base.metadata.tables.keys())
    print("created_tables=" + ",".join(table_names))


if __name__ == "__main__":
    main()
