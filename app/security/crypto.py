from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def generate_document_crypto_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def get_fernet(document_crypto_key: str | None = None) -> Fernet:
    if document_crypto_key is None:
        key = get_settings().document_crypto_key
    else:
        key = document_crypto_key

    if not key:
        raise ValueError("DOCUMENT_CRYPTO_KEY is required")

    return Fernet(key.encode("utf-8"))


def encrypt_bytes(plaintext: bytes, document_crypto_key: str | None = None) -> bytes:
    if not plaintext:
        raise ValueError("plaintext must not be empty")

    return get_fernet(document_crypto_key).encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes, document_crypto_key: str | None = None) -> bytes:
    if not ciphertext:
        raise ValueError("ciphertext must not be empty")

    try:
        return get_fernet(document_crypto_key).decrypt(ciphertext)
    except InvalidToken as exc:
        raise ValueError("invalid ciphertext or key") from exc
