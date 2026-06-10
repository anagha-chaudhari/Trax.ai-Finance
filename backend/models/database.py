from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://finance_user:finance_password@localhost:5432/finance_db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# TABLE 1: users 
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True) # Fixed lowercase 'true' here
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="owner", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"
    
# TABLE 2: reports
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    ticker = Column(String(10), nullable=False, index=True)
    company_name = Column(String, nullable=True)
    
    metrics = Column(JSONB, nullable=True)
    ai_report = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report {self.ticker} for user_id={self.user_id}>"

# TABLE 3: portfolios
class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    ticker = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    
    added_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="portfolios")

    def __repr__(self):
        return f"<Portfolio {self.ticker} qty={self.quantity}>"

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db_session():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()