from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import httpx
import os
import json
import logging
import uuid
from datetime import datetime, timedelta
import time
from jose import JWTError, jwt
from passlib.context import CryptContext
import motor.motor_asyncio
from pymongo import ReturnDocument
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Configuration
class Settings:
    PROJECT_NAME = "Andikar Backend API"
    PROJECT_VERSION = "1.0.0"
    
    # JWT Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Database Settings
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "andikar")
    
    # Service API Endpoints
    HUMANIZER_API_URL = os.getenv("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
    AI_DETECTOR_API_URL = os.getenv("AI_DETECTOR_API_URL", "https://ai-detector-api.example.com")
    
    # M-Pesa Settings
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # in seconds

settings = Settings()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("andikar-backend")

# FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API Gateway for Andikar AI services",
    version=settings.PROJECT_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

# Collections
users_collection = db["users"]
transactions_collection = db["transactions"]
api_logs_collection = db["api_logs"]
rate_limits_collection = db["rate_limits"]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class APIKey(BaseModel):
    api_key: str
    service: str
    issued_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True

class PricingPlan(BaseModel):
    id: str
    name: str
    description: str
    price: float
    word_limit: int
    requests_per_day: int
    features: List[str]

class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    
class UserCreate(UserBase):
    password: str
    plan_id: str = "free"

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

# Text service models
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

# Payment models
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

class Transaction(BaseModel):
    id: str
    user_id: str
    amount: float
    currency: str = "KES"
    payment_method: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}

# Authentication Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user(username: str):
    user = await users_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)
    return None

async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
        
    client_ip = request.client.host
    api_key = request.headers.get("X-API-Key")
    
    # Use API key or IP for rate limiting
    rate_limit_key = api_key if api_key else client_ip
    
    # Check rate limit in database
    now = time.time()
    rate_limit_doc = await rate_limits_collection.find_one({"key": rate_limit_key})
    
    if rate_limit_doc:
        # Clean up old requests
        requests = [req for req in rate_limit_doc["requests"] if now - req < settings.RATE_LIMIT_PERIOD]
        
        # Check if rate limit exceeded
        if len(requests) >= settings.RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Add current request
        requests.append(now)
        await rate_limits_collection.update_one(
            {"key": rate_limit_key},
            {"$set": {"requests": requests, "last_updated": now}}
        )
    else:
        # First request for this key
        await rate_limits_collection.insert_one({
            "key": rate_limit_key,
            "requests": [now],
            "last_updated": now
        })
    
    response = await call_next(request)
    return response

# Authentication Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User Management Endpoints
@app.post("/users/register", response_model=User)
async def register_user(user: UserCreate):
    # Check if username already exists
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await users_collection.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    
    # Check if plan exists (in a real app, would validate against pricing plans table)
    # For demo, we'll just assume it exists
    
    new_user = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "plan_id": user.plan_id,
        "words_used": 0,
        "payment_status": "Pending" if user.plan_id != "free" else "Paid",
        "joined_date": datetime.utcnow(),
        "api_keys": {},
        "is_active": True
    }
    
    await users_collection.insert_one(new_user)
    
    # Remove hashed_password from response
    new_user.pop("hashed_password")
    
    return new_user

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.put("/users/me", response_model=User)
async def update_user(
    user_update: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    # Filter out fields that shouldn't be updated directly
    protected_fields = ["id", "username", "email", "hashed_password", "joined_date"]
    update_data = {k: v for k, v in user_update.items() if k not in protected_fields}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    # Update user in database
    updated_user = await users_collection.find_one_and_update(
        {"id": current_user.id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove hashed_password from response
    updated_user.pop("hashed_password", None)
    
    return updated_user

# API Gateway Endpoints for External Services
@app.post("/api/humanize", response_model=TextResponse)
async def humanize_text_api(
    request: TextRequest,
    current_user: User = Depends(get_current_active_user)
):
    # Check payment status
    if current_user.payment_status != "Paid":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required to access this feature"
        )
    
    # Check word limit
    word_count = len(request.input_text.split())
    max_words = request.max_words
    
    # Log the API request
    log_entry = {
        "user_id": current_user.id,
        "endpoint": "/api/humanize",
        "request_size": word_count,
        "timestamp": datetime.utcnow(),
        "ip_address": "N/A"  # Would normally capture from request
    }
    await api_logs_collection.insert_one(log_entry)
    
    # Call external humanizer API
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.HUMANIZER_API_URL}/humanize_text",
                json={"input_text": request.input_text}
            )
            response.raise_for_status()
            humanized_text = response.json()["result"]
        except httpx.HTTPError as e:
            logger.error(f"Error calling humanizer API: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error connecting to humanizer service"
            )
    
    processing_time = time.time() - start_time
    
    # Update user's word count
    await users_collection.update_one(
        {"id": current_user.id},
        {"$inc": {"words_used": word_count}}
    )
    
    return {
        "result": humanized_text,
        "words_processed": word_count,
        "processing_time": processing_time
    }

@app.post("/api/detect", response_model=DetectionResult)
async def detect_ai_content_api(
    request: TextRequest,
    current_user: User = Depends(get_current_active_user)
):
    # Check payment status
    if current_user.payment_status != "Paid":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required to access this feature"
        )
    
    # Check for detection API URL
    if not settings.AI_DETECTOR_API_URL or settings.AI_DETECTOR_API_URL == "https://ai-detector-api.example.com":
        # Use simplified internal detection if external API not available
        from utils import detect_ai_content
        result = detect_ai_content(request.input_text)
        return result
    
    # Log the API request
    log_entry = {
        "user_id": current_user.id,
        "endpoint": "/api/detect",
        "request_size": len(request.input_text.split()),
        "timestamp": datetime.utcnow(),
        "ip_address": "N/A"  # Would normally capture from request
    }
    await api_logs_collection.insert_one(log_entry)
    
    # Call external AI detection API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.AI_DETECTOR_API_URL}/detect",
                json={"text": request.input_text}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error calling AI detector API: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error connecting to AI detection service"
            )

# M-Pesa Payment Integration
@app.post("/api/payments/mpesa/initiate", response_model=MpesaPaymentResponse)
async def initiate_mpesa_payment(
    payment_request: MpesaPaymentRequest,
    current_user: User = Depends(get_current_active_user)
):
    # Check if M-Pesa credentials are configured
    if not all([
        settings.MPESA_CONSUMER_KEY,
        settings.MPESA_CONSUMER_SECRET,
        settings.MPESA_PASSKEY,
        settings.MPESA_SHORTCODE
    ]):
        logger.warning("M-Pesa credentials not fully configured")
        # For demo purposes, we'll simulate a successful payment initiation
        checkout_request_id = str(uuid.uuid4())
        
        # Create a transaction record
        transaction = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "amount": payment_request.amount,
            "currency": "KES",
            "payment_method": "mpesa",
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {
                "checkout_request_id": checkout_request_id,
                "phone_number": payment_request.phone_number,
                "account_reference": payment_request.account_reference,
                "transaction_desc": payment_request.transaction_desc
            }
        }
        
        await transactions_collection.insert_one(transaction)
        
        return {
            "checkout_request_id": checkout_request_id,
            "response_code": "0",
            "response_description": "Success",
            "customer_message": "Success. Request accepted for processing"
        }
    
    # In a real implementation, this would make an API call to the M-Pesa API
    # For security, we'd need to properly implement OAuth, formatting, etc.
    
    # Simulated response
    return {
        "checkout_request_id": "ws_CO_123456789",
        "response_code": "0",
        "response_description": "Success",
        "customer_message": "Success. Request accepted for processing"
    }

@app.post("/api/payments/mpesa/callback")
async def mpesa_callback(callback: MpesaCallback):
    # This would process the callback from M-Pesa after payment
    
    # Find the corresponding transaction
    transaction = await transactions_collection.find_one(
        {"metadata.checkout_request_id": callback.checkout_request_id}
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Update transaction status
    if callback.result_code == 0:  # Success
        new_status = "completed"
        
        # Update user's payment status
        await users_collection.update_one(
            {"id": transaction["user_id"]},
            {"$set": {"payment_status": "Paid"}}
        )
    else:
        new_status = "failed"
    
    # Update transaction
    await transactions_collection.update_one(
        {"metadata.checkout_request_id": callback.checkout_request_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.utcnow(),
                "metadata.mpesa_receipt_number": callback.mpesa_receipt_number,
                "metadata.transaction_date": callback.transaction_date,
                "metadata.result_desc": callback.result_desc
            }
        }
    )
    
    return {"status": "success"}

# Simulate a payment for testing (in real environment, this would be removed)
@app.post("/api/payments/simulate", response_model=Transaction)
async def simulate_payment(
    amount: float,
    current_user: User = Depends(get_current_active_user)
):
    # Create a transaction record
    transaction_id = str(uuid.uuid4())
    transaction = {
        "id": transaction_id,
        "user_id": current_user.id,
        "amount": amount,
        "currency": "KES",
        "payment_method": "simulation",
        "status": "completed",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "metadata": {
            "simulation": True
        }
    }
    
    await transactions_collection.insert_one(transaction)
    
    # Update user's payment status
    await users_collection.update_one(
        {"id": current_user.id},
        {"$set": {"payment_status": "Paid"}}
    )
    
    return transaction

# Health Check Endpoint
@app.get("/health")
async def health_check():
    # Check database connection
    try:
        # Simple ping to verify MongoDB connection
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    # Check external services
    services_status = {}
    
    # Check Humanizer API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.HUMANIZER_API_URL}/", timeout=5.0)
            services_status["humanizer"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        services_status["humanizer"] = "unhealthy"
    
    # Check AI Detector API (if configured)
    if settings.AI_DETECTOR_API_URL and settings.AI_DETECTOR_API_URL != "https://ai-detector-api.example.com":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.AI_DETECTOR_API_URL}/", timeout=5.0)
                services_status["ai_detector"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services_status["ai_detector"] = "unhealthy"
    else:
        services_status["ai_detector"] = "not_configured"
    
    overall_status = "healthy" if db_status == "healthy" and all(
        status == "healthy" or status == "not_configured" for status in services_status.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            **services_status
        }
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": "Backend API Gateway for Andikar AI services",
        "documentation": "/docs"
    }

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting {settings.PROJECT_NAME} server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)