from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any
from datetime import datetime

# Auth schemas

class UserRegisterRequest(BaseModel):
    """What the frontend sends when a user signs up."""
    email: EmailStr       
    username: str
    password: str

    @field_validator("username")
    def username_must_be_clean(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters")
        return value

    @field_validator("password")
    def password_must_be_strong_enough(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        return value


class UserLoginRequest(BaseModel):
    """What the frontend sends when a user logs in."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """What we send BACK about a user."""
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Returned after successful login."""
    access_token: str
    token_type: str = "bearer"


# Analysis schemas

class AnalysisRequest(BaseModel):
    """What the frontend sends to start an analysis."""
    ticker: str

    @field_validator("ticker")
    def ticker_must_be_valid(cls, value):
        value = value.strip().upper()
        if len(value) > 10:
            raise ValueError("Ticker symbol too long")
        if not value.isalpha() and "." not in value:
            raise ValueError("Invalid ticker format")
        return value


class AnalysisJobResponse(BaseModel):
    """Returned instantly when analysis starts — contains the job ID to poll."""
    job_id: str
    status: str
    message: str


class AnalysisStatusResponse(BaseModel):
    """Returned when frontend polls for job status."""
    job_id: str
    status: str   
    result: Optional[Any] = None 
    error: Optional[str] = None


class ReportResponse(BaseModel):
    """A saved report from the database."""
    id: int
    ticker: str
    company_name: Optional[str]
    metrics: Optional[Any]
    ai_report: Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# Portfolio schemas

class PortfolioAddRequest(BaseModel):
    """Add a stock holding to the portfolio."""
    ticker: str
    quantity: float
    buy_price: float

    @field_validator("quantity", "buy_price")
    def must_be_positive(cls, value):
        if value <= 0:
            raise ValueError("Must be greater than zero")
        return value


class PortfolioResponse(BaseModel):
    """A portfolio entry returned from the API."""
    id: int
    ticker: str
    quantity: float
    buy_price: float
    added_at: datetime

    model_config = {"from_attributes": True}