import pytest

from app.security.crypto import (
    decrypt_bytes,
    encrypt_bytes,
    generate_document_crypto_key,
    get_fernet,
)


def test_generate_document_crypto_key_is_valid_fernet_key():
    key = generate_document_crypto_key()

    assert isinstance(key, str)
    assert get_fernet(key) is not None


def test_encrypt_bytes_does_not_return_plaintext():
    key = generate_document_crypto_key()
    plaintext = b"documento sensivel"

    ciphertext = encrypt_bytes(plaintext, key)

    assert ciphertext != plaintext
    assert plaintext not in ciphertext


def test_decrypt_bytes_restores_plaintext():
    key = generate_document_crypto_key()
    plaintext = b"documento sensivel"

    ciphertext = encrypt_bytes(plaintext, key)

    assert decrypt_bytes(ciphertext, key) == plaintext


def test_decrypt_bytes_rejects_wrong_key():
    correct_key = generate_document_crypto_key()
    wrong_key = generate_document_crypto_key()
    ciphertext = encrypt_bytes(b"documento sensivel", correct_key)

    with pytest.raises(ValueError):
        decrypt_bytes(ciphertext, wrong_key)


def test_encrypt_bytes_rejects_empty_plaintext():
    key = generate_document_crypto_key()

    with pytest.raises(ValueError):
        encrypt_bytes(b"", key)


def test_decrypt_bytes_rejects_empty_ciphertext():
    key = generate_document_crypto_key()

    with pytest.raises(ValueError):
        decrypt_bytes(b"", key)


def test_get_fernet_requires_key():
    with pytest.raises(ValueError):
        get_fernet("")
