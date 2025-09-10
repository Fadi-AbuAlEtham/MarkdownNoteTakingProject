from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt

SECRET_KEY = "EXALT_SUMMER_TRAINING"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(
    subject: str | int, expires_delta: Optional[timedelta] = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    # Raises jose.JWTError (or ExpiredSignatureError) on failure
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
