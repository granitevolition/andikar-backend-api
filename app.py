"""
Core application file for Andikar Backend API.
This module provides a backend API gateway for the Andikar AI ecosystem.
"""
import logging
import os
import time
from datetime import datetime, timedelta
import json
import uuid
import httpx
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text, desc, func
from typing import List, Optional, Dict, Any, Union
import time
from pathlib import Path

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("andikar-backend-api")

# App configuration
PROJECT_NAME = "Andikar Backend API"
PROJECT_VERSION = "1.0.1"
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
HUMANIZER_API_URL = os.getenv("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
AI_DETECTOR_API_URL = os.getenv("AI_DETECTOR_API_URL", "https://ai-detector-api.example.com")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # 1 hour in seconds

# Database setup - will be imported dynamically to avoid startup errors
db = None
models = None

# Authentication utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    description="Backend API Gateway for Andikar AI services",
    version=PROJECT_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Set up templates
try:
    templates = Jinja2Templates(directory="templates")
except Exception as e:
    logger.warning(f"Could not initialize templates: {e}")
    templates = None

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    plan_id: str = "free"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None

class User(UserBase):
    id: str
    plan_id: str
    words_used: int
    payment_status: str
    joined_date: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class TextRequest(BaseModel):
    input_text: str

class TextResponse(BaseModel):
    result: str
    words_processed: int
    processing_time: float

class DetectionResult(BaseModel):
    ai_score: float
    human_score: float
    analysis: Dict[str, float]

class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float
    account_reference: str = "Andikar Payment"
    transaction_desc: str = "Payment for Andikar AI services"

class MpesaPaymentResponse(BaseModel):
    checkout_request_id: str
    response_code: str
    response_description: str
    customer_message: str

class MpesaCallback(BaseModel):
    checkout_request_id: str
    result_code: int
    result_desc: str
    mpesa_receipt_number: Optional[str] = None
    transaction_date: Optional[str] = None

class Transaction(BaseModel):
    id: str
    user_id: str
    amount: float
    currency: str
    payment_method: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Initialize database and models
try:
    from database import get_db, engine
    import models as db_models
    from models import Base, User as UserModel
    
    db = get_db
    models = db_models
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    
    # Provide mock get_db function for testing
    def get_db():
        yield None

# Auth functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db, username: str, password: str):
    if db is None:
        return None
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if db is None:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: models.User = Depends(get_current_user)):
    # For now, just check if the user is the admin user (username 'admin')
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access admin area"
        )
    return current_user

# API exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        # If it's a known FastAPI HTTP exception, let FastAPI handle it
        raise exc
    
    logger.error(f"Unexpected error: {str(exc)}")
    import traceback
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") == "1" else "An unexpected error occurred"
        }
    )

# Root endpoint - serves index.html
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if templates:
        try:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "title": PROJECT_NAME,
                "description": "Backend API Gateway for Andikar AI services",
                "version": PROJECT_VERSION,
                "status": "healthy",
                "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production"),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
    
    # If templates fail or aren't available, return a basic JSON response
    return JSONResponse({
        "status": "healthy",
        "name": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "description": "Backend API Gateway for Andikar AI services",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")
    })

# Status endpoint for healthcheck
@app.get("/status")
async def status_check():
    return {
        "status": "healthy",
        "message": "Application is running",
        "progress": 100,
        "complete": True
    }

# Health check endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    db_status = "unknown"
    
    if db is not None:
        try:
            db.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_status = f"unhealthy: {str(e)}"
    else:
        db_status = "unavailable"
    
    # Check Humanizer API
    humanizer_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HUMANIZER_API_URL}/", timeout=5.0)
            humanizer_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        logger.error(f"Error checking humanizer API: {str(e)}")
        humanizer_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" and humanizer_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "humanizer_api": humanizer_status,
            "api": "healthy"
        }
    }

# Authentication Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User Management Endpoints
@app.post("/users/register", response_model=User)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    
    # Check if plan exists
    plan = db.query(models.PricingPlan).filter(models.PricingPlan.id == user.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{user.plan_id}' does not exist"
        )
    
    new_user = models.User(
        id=str(uuid.uuid4()),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        plan_id=user.plan_id,
        payment_status="Pending" if user.plan_id != "free" else "Paid",
        words_used=0,
        joined_date=datetime.utcnow(),
        api_keys={},
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@app.put("/users/me", response_model=User)
async def update_user(
    user_update: UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Update user fields
    user_data = user_update.model_dump(exclude_unset=True)
    
    if user_data:
        for key, value in user_data.items():
            setattr(current_user, key, value)
        
        db.commit()
        db.refresh(current_user)
    
    return current_user

# API Gateway Endpoints for External Services
@app.post("/api/humanize", response_model=TextResponse)
async def humanize_text_api(
    request: TextRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Check payment status
    if current_user.payment_status != "Paid":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required to access this feature"
        )
    
    # Check word limit
    word_count = len(request.input_text.split())
    
    # Get user's plan details
    plan = db.query(models.PricingPlan).filter(models.PricingPlan.id == current_user.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan associated with user"
        )
    
    # Check word limit against plan
    if word_count > plan.word_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Word count exceeds plan limit ({word_count} > {plan.word_limit})"
        )
    
    # Log the API request
    log_entry = models.APILog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        endpoint="/api/humanize",
        request_size=word_count,
        ip_address=None  # Would normally capture from request
    )
    db.add(log_entry)
    db.commit()
    
    # Call external humanizer API
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HUMANIZER_API_URL}/humanize_text",
                json={"input_text": request.input_text},
                timeout=30.0
            )
            response.raise_for_status()
            humanized_text = response.json()["result"]
    except httpx.HTTPError as e:
        logger.error(f"Error calling humanizer API: {str(e)}")
        
        # Update log entry with error information
        log_entry.error = str(e)
        log_entry.status_code = 503
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error connecting to humanizer service"
        )
    
    processing_time = time.time() - start_time
    
    # Update log entry with response information
    log_entry.response_size = len(humanized_text.split())
    log_entry.processing_time = processing_time
    log_entry.status_code = 200
    
    # Update user's word count
    current_user.words_used += word_count
    
    # Update usage statistics
    today = datetime.utcnow()
    usage_stat = db.query(models.UsageStat).filter(
        models.UsageStat.user_id == current_user.id,
        models.UsageStat.year == today.year,
        models.UsageStat.month == today.month,
        models.UsageStat.day == today.day
    ).first()
    
    if usage_stat:
        usage_stat.humanize_requests += 1
        usage_stat.words_processed += word_count
        usage_stat.total_processing_time += processing_time
    else:
        new_usage_stat = models.UsageStat(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            year=today.year,
            month=today.month,
            day=today.day,
            humanize_requests=1,
            detect_requests=0,
            words_processed=word_count,
            total_processing_time=processing_time
        )
        db.add(new_usage_stat)
    
    db.commit()
    
    return {
        "result": humanized_text,
        "words_processed": word_count,
        "processing_time": processing_time
    }

@app.post("/api/detect", response_model=DetectionResult)
async def detect_ai_content_api(
    request: TextRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Check payment status
    if current_user.payment_status != "Paid":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required to access this feature"
        )
    
    # Log the API request
    word_count = len(request.input_text.split())
    log_entry = models.APILog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        endpoint="/api/detect",
        request_size=word_count,
        ip_address=None  # Would normally capture from request
    )
    db.add(log_entry)
    db.commit()
    
    # Simple detection algorithm for demo
    start_time = time.time()
    
    # Calculate AI likelihood based on simple heuristics
    formal_indicators = ["furthermore", "additionally", "moreover", "thus", "therefore", 
                         "consequently", "hence", "as a result", "in conclusion"]
    indicator_count = sum(request.input_text.lower().count(indicator) for indicator in formal_indicators)
    
    # Calculate sentence variety
    sentences = request.input_text.split(".")
    sentence_lengths = [len(s.strip()) for s in sentences if s.strip()]
    length_uniformity = 0
    if sentence_lengths:
        mean_length = sum(sentence_lengths) / len(sentence_lengths)
        std_dev = (sum((l - mean_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)) ** 0.5
        length_uniformity = std_dev / mean_length if mean_length > 0 else 0
    
    # Calculate AI score
    ai_score = min(100, max(0, 20 + (indicator_count * 5) + (50 * (1 - length_uniformity))))
    
    processing_time = time.time() - start_time
    
    # Update database
    log_entry.processing_time = processing_time
    log_entry.status_code = 200
    
    today = datetime.utcnow()
    usage_stat = db.query(models.UsageStat).filter(
        models.UsageStat.user_id == current_user.id,
        models.UsageStat.year == today.year,
        models.UsageStat.month == today.month,
        models.UsageStat.day == today.day
    ).first()
    
    if usage_stat:
        usage_stat.detect_requests += 1
        usage_stat.words_processed += word_count
        usage_stat.total_processing_time += processing_time
    else:
        new_usage_stat = models.UsageStat(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            year=today.year,
            month=today.month,
            day=today.day,
            humanize_requests=0,
            detect_requests=1,
            words_processed=word_count,
            total_processing_time=processing_time
        )
        db.add(new_usage_stat)
    
    db.commit()
    
    return {
        "ai_score": round(ai_score, 1),
        "human_score": round(100 - ai_score, 1),
        "analysis": {
            "formal_language": min(100, indicator_count * 10),
            "sentence_uniformity": min(100, (1 - length_uniformity) * 100),
            "repetitive_patterns": min(100, ai_score * 0.5)
        }
    }

# Admin dashboard metrics endpoint
@app.get("/dashboard")
async def get_dashboard_data(current_user: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Get user stats
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar() or 0
    
    # Get API usage stats
    total_requests = db.query(func.count(models.APILog.id)).scalar() or 0
    humanize_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/humanize"
    ).scalar() or 0
    detect_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/detect"
    ).scalar() or 0
    
    # Success rate
    successful_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.status_code == 200
    ).scalar() or 0
    api_success = round((successful_requests / total_requests) * 100) if total_requests > 0 else 100
    
    # Get recent transactions
    recent_transactions = []
    transactions = db.query(models.Transaction).order_by(desc(models.Transaction.created_at)).limit(5).all()
    
    for tx in transactions:
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()
        username = user.username if user else "Unknown"
        
        recent_transactions.append({
            "txId": tx.id[:8],
            "user": username,
            "date": tx.created_at.isoformat(),
            "cost": tx.amount
        })
    
    # Generate usage data for chart
    days = 30
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days-1)
    
    usage_data = []
    dates = []
    humanize_values = []
    detect_values = []
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        dates.append(current_date.strftime("%Y-%m-%d"))
        
        # Get humanize requests for this date
        humanize_count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == "/api/humanize",
            func.cast(models.APILog.timestamp, db.DateTime).between(
                datetime.combine(current_date, datetime.min.time()),
                datetime.combine(current_date, datetime.max.time())
            )
        ).scalar() or 0
        
        humanize_values.append(humanize_count)
        
        # Get detect requests for this date
        detect_count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == "/api/detect",
            func.cast(models.APILog.timestamp, db.DateTime).between(
                datetime.combine(current_date, datetime.min.time()),
                datetime.combine(current_date, datetime.max.time())
            )
        ).scalar() or 0
        
        detect_values.append(detect_count)
    
    # Format for chart
    usage_data = [
        {
            "id": "API Humanize",
            "color": "hsl(94, 70%, 50%)",
            "data": [{"x": date, "y": value} for date, value in zip(dates, humanize_values)]
        },
        {
            "id": "API Detect",
            "color": "hsl(241, 70%, 50%)",
            "data": [{"x": date, "y": value} for date, value in zip(dates, detect_values)]
        }
    ]
    
    # API distribution for pie chart
    api_distribution = [
        {
            "id": "Humanize API",
            "label": "Humanize API",
            "value": humanize_requests,
            "color": "hsl(94, 70%, 50%)"
        },
        {
            "id": "Detect API",
            "label": "Detect API",
            "value": detect_requests,
            "color": "hsl(241, 70%, 50%)"
        }
    ]
    
    return {
        "totalUsers": total_users,
        "totalRequests": total_requests,
        "activeUsers": active_users,
        "apiSuccess": api_success,
        "apiErrors": 100 - api_success,
        "recentTransactions": recent_transactions,
        "usageData": usage_data,
        "apiDistribution": api_distribution
    }

# M-Pesa Payment Integration
@app.post("/api/payments/mpesa/initiate", response_model=MpesaPaymentResponse)
async def initiate_mpesa_payment(
    payment_request: MpesaPaymentRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Simulate a successful payment initiation
    checkout_request_id = str(uuid.uuid4())
    
    # Create a transaction record
    transaction = models.Transaction(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        amount=payment_request.amount,
        currency="KES",
        payment_method="mpesa",
        status="pending",
        transaction_metadata={
            "checkout_request_id": checkout_request_id,
            "phone_number": payment_request.phone_number,
            "account_reference": payment_request.account_reference,
            "transaction_desc": payment_request.transaction_desc
        }
    )
    
    db.add(transaction)
    db.commit()
    
    return {
        "checkout_request_id": checkout_request_id,
        "response_code": "0",
        "response_description": "Success",
        "customer_message": "Success. Request accepted for processing"
    }

@app.post("/api/payments/mpesa/callback")
async def mpesa_callback(
    callback: MpesaCallback,
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Find the corresponding transaction
    transaction = db.query(models.Transaction).filter(
        models.Transaction.transaction_metadata.contains({"checkout_request_id": callback.checkout_request_id})
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Update transaction status
    if callback.result_code == 0:  # Success
        transaction.status = "completed"
        
        # Update user's payment status
        user = db.query(models.User).filter(models.User.id == transaction.user_id).first()
        if user:
            user.payment_status = "Paid"
            db.commit()
    else:
        transaction.status = "failed"
    
    # Update transaction metadata
    transaction.transaction_metadata.update({
        "mpesa_receipt_number": callback.mpesa_receipt_number,
        "transaction_date": callback.transaction_date,
        "result_desc": callback.result_desc
    })
    
    db.commit()
    
    return {"status": "success"}

# Simulate a payment for testing
@app.post("/api/payments/simulate", response_model=Transaction)
async def simulate_payment(
    amount: float,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    # Create a transaction record
    transaction = models.Transaction(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        amount=amount,
        currency="KES",
        payment_method="simulation",
        status="completed",
        transaction_metadata={"simulation": True}
    )
    
    db.add(transaction)
    
    # Update user's payment status
    current_user.payment_status = "Paid"
    
    db.commit()
    db.refresh(transaction)
    
    return transaction

# Alternative index page routes
@app.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request):
    return await root(request)

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return await root(request)

# Admin routes will be included in startup

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting {PROJECT_NAME} server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
