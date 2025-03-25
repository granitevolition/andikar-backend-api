from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    plan_id = Column(String, default="free")
    words_used = Column(Integer, default=0)
    payment_status = Column(String, default="Pending")
    joined_date = Column(DateTime, default=datetime.datetime.utcnow)
    api_keys = Column(JSON, default=lambda: {})
    is_active = Column(Boolean, default=True)

    transactions = relationship("Transaction", back_populates="user")
    api_logs = relationship("APILog", back_populates="user")
    rate_limits = relationship("RateLimit", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    amount = Column(Float)
    currency = Column(String, default="KES")
    payment_method = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    metadata = Column(JSON, default=lambda: {})

    user = relationship("User", back_populates="transactions")

class APILog(Base):
    __tablename__ = "api_logs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    endpoint = Column(String)
    request_size = Column(Integer)
    response_size = Column(Integer, nullable=True)
    processing_time = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    error = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    user = relationship("User", back_populates="api_logs")

class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    key = Column(String, unique=True)
    requests = Column(JSON, default=lambda: [])
    last_updated = Column(Float, default=lambda: datetime.datetime.utcnow().timestamp())

    user = relationship("User", back_populates="rate_limits")

class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)
    currency = Column(String, default="KES")
    billing_cycle = Column(String, default="monthly")
    word_limit = Column(Integer)
    requests_per_day = Column(Integer)
    features = Column(JSON, default=lambda: [])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    url = Column(String)
    events = Column(JSON, default=lambda: [])
    secret = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_triggered = Column(JSON, nullable=True)

class UsageStat(Base):
    __tablename__ = "usage_stats"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    year = Column(Integer)
    month = Column(Integer)
    day = Column(Integer)
    humanize_requests = Column(Integer, default=0)
    detect_requests = Column(Integer, default=0)
    words_processed = Column(Integer, default=0)
    total_processing_time = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
