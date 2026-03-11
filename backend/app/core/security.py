from datetime import datetime, timedelta, timezone
import re
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)


def validate_password_strength(password: str):
    """Apply a minimum password policy for auth and user management flows."""
    if len(password or "") < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(
            "Senha deve ter pelo menos {} caracteres".format(
                settings.PASSWORD_MIN_LENGTH
            )
        )
    if not re.search(r"[A-Za-z]", password or ""):
        raise ValueError("Senha deve conter ao menos uma letra")
    if not re.search(r"\d", password or ""):
        raise ValueError("Senha deve conter ao menos um numero")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode a JWT token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
