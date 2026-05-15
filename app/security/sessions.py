from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings


def _get_serializer(secret_key: str | None = None) -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(
        secret_key or settings.app_secret_key,
        salt="securedocs-session",
    )


def create_session_token(user_id: int, secret_key: str | None = None) -> str:
    if user_id <= 0:
        raise ValueError("user_id must be positive")

    serializer = _get_serializer(secret_key)
    return serializer.dumps({"user_id": user_id})


def verify_session_token(
    token: str | None,
    *,
    max_age_seconds: int | None = None,
    secret_key: str | None = None,
) -> int | None:
    if not token:
        return None

    settings = get_settings()
    serializer = _get_serializer(secret_key)
    max_age = max_age_seconds if max_age_seconds is not None else settings.session_max_age_seconds

    try:
        data = serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

    user_id = data.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        return None

    return user_id
