from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)


def test_create_tokens_with_non_default_params():
    subject = "test_user_id"
    additional_claims = {"role": "user"}

    access_token = create_access_token(
        subject=subject,
        expires_delta=timedelta(minutes=20),
        additional_claims=additional_claims,
    )
    refresh_token = create_refresh_token(
        subject=subject,
        expires_delta=timedelta(days=14),
        additional_claims=additional_claims,
    )

    assert access_token is not None
    assert refresh_token is not None

    decoded_access = decode_token(access_token)
    decoded_refresh = decode_token(refresh_token)

    assert decoded_access["sub"] == subject
    assert decoded_access["type"] == "access"
    assert decoded_access["role"] == "user"

    # 20 minutes in seconds
    assert decoded_access["exp"] == decoded_access["iat"] + 20 * 60

    assert decoded_refresh["sub"] == subject
    assert decoded_refresh["type"] == "refresh"
    assert decoded_refresh["role"] == "user"

    # 14 days in seconds
    assert decoded_refresh["exp"] == decoded_refresh["iat"] + 14 * 24 * 60 * 60


def test_verify_token_wrong_type():
    access_token = create_access_token(subject="test_user_id")

    user_id = verify_token(access_token, token_type="wrong_type")

    assert user_id is None
