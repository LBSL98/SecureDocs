import pytest

from app.security.sessions import create_session_token, verify_session_token


def test_create_and_verify_session_token():
    token = create_session_token(10, secret_key="test-secret")
    assert verify_session_token(token, secret_key="test-secret") == 10


def test_verify_session_token_rejects_wrong_secret():
    token = create_session_token(10, secret_key="test-secret")
    assert verify_session_token(token, secret_key="other-secret") is None


def test_verify_session_token_rejects_empty_token():
    assert verify_session_token(None, secret_key="test-secret") is None
    assert verify_session_token("", secret_key="test-secret") is None


def test_create_session_token_rejects_invalid_user_id():
    with pytest.raises(ValueError):
        create_session_token(0, secret_key="test-secret")


def test_verify_session_token_rejects_expired_token():
    token = create_session_token(10, secret_key="test-secret")
    assert verify_session_token(token, max_age_seconds=-1, secret_key="test-secret") is None
