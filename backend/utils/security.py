from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from utils.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Password functions

# Takes a plain text password and returns a bcrypt hash
def hash_password(plain_password: str) -> str:
    return password_context.hash(plain_password)

# Checks if plain password matches a stored hash.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


# JWT functions

#Creates a signed JWT token containing users ID.
def create_access_token(user_id: int) -> str:
    token_expiry = datetime.utcnow() + timedelta(
        minutes=settings.jwt_expire_minutes
    )

    token_payload = {
        "sub": str(user_id),   # "sub" = subject, JWT standard field
        "exp": token_expiry,   # "exp" = expiry, JWT standard field
    }

    signed_token = jwt.encode(
        token_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return signed_token

# Verifies a jwt token and extracts the user_id from it.
def decode_access_token(token: str) -> Optional[int]:
    try:
        decoded_payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id_string = decoded_payload.get("sub")

        if user_id_string is None:
            return None

        return int(user_id_string)

    except JWTError:
        return None


# Fast API dependency

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from models.database import get_db_session, User

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db_session: Session = Depends(get_db_session)
) -> User:
    
    # Define the error we'll raise if anything is wrong
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode the token
    user_id = decode_access_token(credentials.credentials)

    if user_id is None:
        raise auth_error

    # Look up the user in the database
    user = db_session.query(User).filter(User.id == user_id).first()

    if user is None:
        raise auth_error

    return user