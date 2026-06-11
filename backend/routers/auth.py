from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db_session, User
from models.schemas import (UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse)
from utils.security import hash_password, verify_password, create_access_token, get_current_user


# Creating router for all authentication-related APIs
router = APIRouter()


# Register new user
@router.post("/register",
             response_model=UserResponse,
             status_code=status.HTTP_201_CREATED,
)
def register(
    request: UserRegisterRequest,
    db_session: Session = Depends(get_db_session),
):
    """
    API to create a new user account.
    FastAPI automatically validates the input fields
    before entering this function.
    """

    # Check whether the email is already registered
    existing_user = (
        db_session.query(User)
        .filter(User.email == request.email)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Check whether the username is already taken
    existing_username = (
        db_session.query(User)
        .filter(User.username == request.username)
        .first()
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    # Convert password into a secure hashed format
    safe_password = hash_password(request.password)

    # Create new user object
    new_user = User(
        email=request.email,
        username=request.username,
        hashed_password=safe_password,
    )

    # Save user details in the database
    db_session.add(new_user)
    db_session.commit()

    # Refresh to get generated values like id
    db_session.refresh(new_user)

    # Return user details (password not included)
    return new_user


# User login
@router.post("/login", response_model=TokenResponse)
def login(
    request: UserLoginRequest,
    db_session: Session = Depends(get_db_session),
):
    """
    API for user login.
    If credentials are correct,
    a JWT access token is returned.
    """

    # Find user using email
    user = (
        db_session.query(User)
        .filter(User.email == request.email)
        .first()
    )

    # Common error for invalid login details
    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )

    if user is None:
        raise invalid_credentials_error

    # Check if entered password matches stored password
    password_is_correct = verify_password(request.password, user.hashed_password)

    if not password_is_correct:
        raise invalid_credentials_error

    # Generate JWT token after successful login
    access_token = create_access_token(user_id=user.id)

    return TokenResponse(access_token=access_token)


# Get current logged-in user details
@router.get("/me", response_model=UserResponse)
def get_my_profile(
    # Current user is obtained from JWT token
    current_user: User = Depends(get_current_user),
):
    return current_user

