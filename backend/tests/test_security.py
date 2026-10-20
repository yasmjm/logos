from app.core.security import hash_password, verify_password


def test_hash_password_verifies_correct_password() -> None:
    password_hash = hash_password("logos123")

    assert password_hash.startswith("scrypt$")
    assert verify_password("logos123", password_hash)


def test_verify_password_rejects_wrong_password() -> None:
    assert not verify_password("wrong", hash_password("logos123"))


def test_hash_password_uses_random_salt() -> None:
    assert hash_password("logos123") != hash_password("logos123")


def test_verify_password_rejects_malformed_hash() -> None:
    assert not verify_password("logos123", "not-a-hash")
