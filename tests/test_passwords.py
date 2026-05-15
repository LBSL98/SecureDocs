from app.security.passwords import hash_password, verify_password


def test_hash_password_does_not_store_plaintext():
    password_hash = hash_password("SenhaSegura123!")
    assert password_hash != "SenhaSegura123!"
    assert "SenhaSegura123!" not in password_hash
    assert password_hash.startswith(chr(36) + "argon2")


def test_verify_password_accepts_correct_password():
    password_hash = hash_password("SenhaSegura123!")
    assert verify_password("SenhaSegura123!", password_hash) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("SenhaSegura123!")
    assert verify_password("senha-errada", password_hash) is False
