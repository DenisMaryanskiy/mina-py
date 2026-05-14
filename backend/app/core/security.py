from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logger import get_logger

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4,  # 4 parallel threads
    bcrypt__rounds=12,  # 2^12 = 4096 iterations
)

settings = get_settings()


def hash_password(password: str) -> str:
    """
    Hash a password using a secure hashing algorithms: Argon2id or bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token with the given subject and expiration time.

    :param subject: The subject (e.g., user ID) to include in the token.
    :param expires_delta: Optional timedelta for token expiration.
        Defaults to 15 minutes.
    :param additional_claims: Optional dictionary of additional claims
        to include in the token.

    :return: The encoded JWT token as a string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"sub": subject, "exp": expire, "iat": now, "type": "access"}

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT refresh token with the given subject and expiration time.

    :param subject: The subject (e.g., user ID) to include in the token.
    :param expires_delta: Optional timedelta for token expiration.
        Defaults to 7 days.
    :param additional_claims: Optional dictionary of additional claims
        to include in the token.

    :return: The encoded JWT token as a string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"sub": subject, "exp": expire, "iat": now, "type": "refresh"}

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode a JWT token and return its claims.

    :param token: The JWT token to decode.
    :return: A dictionary of the token's claims.
    :raises JWTError: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Token decoding failed: {str(e)}") from e


def verify_token(token: str, token_type: str = "access") -> str | None:
    """
    Verify that the token is of the expected type (access or refresh).

    :param token: The JWT token to verify.
    :param token_type: The expected token type ('access' or 'refresh').
    :return: The subject (e.g., user ID) if the token is valid and
        of the correct type, otherwise None.
    :raises JWTError: If the token is invalid or expired.
    """
    logger = get_logger()
    try:
        payload = decode_token(token)

        payload_type = payload.get("type")
        if payload_type != token_type:
            logger.warning(
                "Token type mismatch: expected '%s', got '%s'",
                token_type,
                payload_type,
            )
            return None

        user_id = payload.get("sub")
        return user_id
    except JWTError as e:
        logger.warning("Token verification failed: %s", str(e))
        return None
