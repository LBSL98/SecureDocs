from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.audit_service import create_audit_log, list_audit_logs


def make_test_db(tmp_path):
    database_path = tmp_path / "test_audit_service.db"
    engine = create_engine(
        "sqlite:///" + str(database_path),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session


def test_create_audit_log_persists_event(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        event = create_audit_log(
            db,
            actor_user_id=1,
            action="login",
            outcome="success",
            target_type="user",
            target_id="1",
            ip_address="127.0.0.1",
            user_agent="pytest",
            details="login successful",
        )

        stored = list_audit_logs(db)

    assert event.id is not None
    assert len(stored) == 1
    assert stored[0].action == "login"
    assert stored[0].outcome == "success"
    assert stored[0].details == "login successful"


def test_list_audit_logs_limits_results(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        for index in range(3):
            create_audit_log(
                db,
                action="event",
                outcome="success",
                details="event " + str(index),
            )

        stored = list_audit_logs(db, limit=2)

    assert len(stored) == 2


def test_list_audit_logs_enforces_minimum_limit(tmp_path):
    testing_session = make_test_db(tmp_path)

    with testing_session() as db:
        create_audit_log(db, action="event", outcome="success")
        stored = list_audit_logs(db, limit=0)

    assert len(stored) == 1
