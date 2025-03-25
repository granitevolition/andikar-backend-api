from pydantic import BaseModel, Field, EmailStr, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    plan_id: str = "free"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    plan_id: Optional[str] = None
    api_keys: Optional[Dict[str, str]] = None

class User(UserBase):
    id: str
    plan_id: str
    words_used: int = 0
    payment_status: str = "Pending"
    joined_date: datetime
    api_keys: Dict[str, str] = {}
    is_active: bool = True

    class Config:
        orm_mode = True

class UserInDB(User):
    hashed_password: str

# Text service schemas
class TextRequest(BaseModel):
    input_text: str
    max_words: Optional[int] = None

class TextResponse(BaseModel):
    result: str
    words_processed: int
    processing_time: float

class DetectionResult(BaseModel):
    ai_score: float
    human_score: float
    analysis: Dict[str, Any]

# Payment schemas
class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float
    account_reference: str
    transaction_desc: str

class MpesaPaymentResponse(BaseModel):
    checkout_request_id: str
    response_code: str
    response_description: str
    customer_message: str

class MpesaCallback(BaseModel):
    result_code: int
    result_desc: str
    checkout_request_id: str
    amount: float
    mpesa_receipt_number: Optional[str] = None
    transaction_date: Optional[str] = None
    phone_number: Optional[str] = None

class TransactionBase(BaseModel):
    amount: float
    currency: str = "KES"
    payment_method: str
    metadata: Dict[str, Any] = {}

class TransactionCreate(TransactionBase):
    user_id: str
    status: str = "pending"

class Transaction(TransactionBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Pricing plan schemas
class PricingPlanBase(BaseModel):
    name: str
    description: str
    price: float
    currency: str = "KES"
    billing_cycle: str = "monthly"
    word_limit: int
    requests_per_day: int
    features: List[str] = []

class PricingPlanCreate(PricingPlanBase):
    id: str

class PricingPlan(PricingPlanBase):
    id: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# API log schemas
class APILogCreate(BaseModel):
    user_id: str
    endpoint: str
    request_size: int
    response_size: Optional[int] = None
    processing_time: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class APILog(APILogCreate):
    id: str
    timestamp: datetime

    class Config:
        orm_mode = True

# Rate limit schemas
class RateLimitCreate(BaseModel):
    key: str
    user_id: Optional[str] = None
    requests: List[float] = []
    last_updated: float

class RateLimit(RateLimitCreate):
    id: str

    class Config:
        orm_mode = True

# Webhook schemas
class WebhookBase(BaseModel):
    url: str
    events: List[str]
    secret: str

class WebhookCreate(WebhookBase):
    user_id: str

class Webhook(WebhookBase):
    id: str
    user_id: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_triggered: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

# Usage stats schemas
class UsageStatCreate(BaseModel):
    user_id: str
    year: int
    month: int
    day: int
    humanize_requests: int = 0
    detect_requests: int = 0
    words_processed: int = 0
    total_processing_time: float = 0

class UsageStat(UsageStatCreate):
    id: str
    updated_at: datetime

    class Config:
        orm_mode = True
