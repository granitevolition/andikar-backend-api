from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, List, Optional, Any, Union
import httpx
import os
import json
import logging
import time
import sys
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
import traceback

# Import database and models
from database import get_db, engine
import models
import schemas
from models import Base
from utils import detect_ai_content

# Import admin routes
from admin import admin_router

# Configuration
class Settings:
    PROJECT_NAME = "Andikar Backend API"
    PROJECT_VERSION = "1.0.5"
    
    # JWT Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        # If it's a known FastAPI HTTP exception, let FastAPI handle it
        raise exc
    
    # For unexpected errors, log them and return a generic error
    logger.error(f"Unexpected error: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") == "1" else "An unexpected error occurred"
        }
    )

# Authentication Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
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

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        return None
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = schemas.TokenData(username=username)
    except JWTError:
        return None
    user = get_user(db, username=token_data.username)
    if user is None:
        return None
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ["/docs", "/redoc", "/openapi.json", "/", "/health"] or request.url.path.startswith("/admin") or request.url.path.startswith("/static"):
        return await call_next(request)
    
    try:
        # Get the database session
        db = next(get_db())
        
        client_ip = request.client.host
        api_key = request.headers.get("X-API-Key")
        
        # Use API key or IP for rate limiting
        rate_limit_key = api_key if api_key else client_ip
        
        # Check rate limit in database
        now = time.time()
        rate_limit = db.query(models.RateLimit).filter(models.RateLimit.key == rate_limit_key).first()
        
        if rate_limit:
            # Clean up old requests
            requests = [req for req in rate_limit.requests if now - req < settings.RATE_LIMIT_PERIOD]
            
            # Check if rate limit exceeded
            if len(requests) >= settings.RATE_LIMIT_REQUESTS:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"}
                )
            
            # Add current request
            requests.append(now)
            rate_limit.requests = requests
            rate_limit.last_updated = now
            db.commit()
        else:
            # First request for this key
            new_rate_limit = models.RateLimit(
                key=rate_limit_key,
                requests=[now],
                last_updated=now
            )
            db.add(new_rate_limit)
            db.commit()
    except Exception as e:
        # If rate limiting fails, just log and continue
        logger.error(f"Rate limiting failed: {str(e)}")
    
    response = await call_next(request)
    return response

# Database initialization
@app.on_event("startup")
async def startup_db_client():
    try:
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        # Initialize default pricing plans if they don't exist
        db = next(get_db())
        if db.query(models.PricingPlan).count() == 0:
            default_plans = [
                models.PricingPlan(
                    id="free",
                    name="Free Plan",
                    description="Basic features for trying out the service",
                    price=0,
                    word_limit=1000,
                    requests_per_day=10,
                    features=["Humanize text (limited)", "AI detection (limited)"]
                ),
                models.PricingPlan(
                    id="basic",
                    name="Basic Plan",
                    description="Standard features for regular users",
                    price=999.00,
                    word_limit=10000,
                    requests_per_day=50,
                    features=["Humanize text", "AI detection", "Email support"]
                ),
                models.PricingPlan(
                    id="premium",
                    name="Premium Plan",
                    description="Advanced features for professional users",
                    price=2999.00,
                    word_limit=50000,
                    requests_per_day=100,
                    features=["Humanize text", "AI detection", "Priority support", "API access"]
                )
            ]
            db.add_all(default_plans)
            db.commit()
        
        # Create an admin user if it doesn't exist
        if not db.query(models.User).filter(models.User.username == "admin").first():
            admin_user = models.User(
                username="admin",
                email="admin@andikar.com",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),  # Change this password in production!
                plan_id="premium",
                payment_status="Paid",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default admin user")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())
        # Don't crash the app if there's an issue during initialization
        # It will be caught and reported when API endpoints are accessed

# Authentication Endpoints
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
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
@app.post("/users/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
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
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        plan_id=user.plan_id,
        payment_status="Pending" if user.plan_id != "free" else "Paid"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@app.put("/users/me", response_model=schemas.User)
async def update_user(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Update user fields
    user_data = user_update.dict(exclude_unset=True)
    
    if user_data:
        for key, value in user_data.items():
            setattr(current_user, key, value)
        
        db.commit()
        db.refresh(current_user)
    
    return current_user

# API Gateway Endpoints for External Services
@app.post("/api/humanize", response_model=schemas.TextResponse)
async def humanize_text_api(
    request: schemas.TextRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
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
        user_id=current_user.id,
        endpoint="/api/humanize",
        request_size=word_count,
        ip_address="N/A"  # Would normally capture from request
    )
    db.add(log_entry)
    db.commit()
    
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
            user_id=current_user.id,
            year=today.year,
            month=today.month,
            day=today.day,
            humanize_requests=1,
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

@app.post("/api/detect", response_model=schemas.DetectionResult)
async def detect_ai_content_api(
    request: schemas.TextRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check payment status
    if current_user.payment_status != "Paid":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required to access this feature"
        )
    
    # Log the API request
    word_count = len(request.input_text.split())
    log_entry = models.APILog(
        user_id=current_user.id,
        endpoint="/api/detect",
        request_size=word_count,
        ip_address="N/A"  # Would normally capture from request
    )
    db.add(log_entry)
    db.commit()
    
    # Check for detection API URL
    start_time = time.time()
    if not settings.AI_DETECTOR_API_URL or settings.AI_DETECTOR_API_URL == "https://ai-detector-api.example.com":
        # Use simplified internal detection if external API not available
        result = detect_ai_content(request.input_text)
        processing_time = time.time() - start_time
        
        # Update log entry with response information
        log_entry.processing_time = processing_time
        log_entry.status_code = 200
        
        # Update usage statistics
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
                user_id=current_user.id,
                year=today.year,
                month=today.month,
                day=today.day,
                detect_requests=1,
                words_processed=word_count,
                total_processing_time=processing_time
            )
            db.add(new_usage_stat)
        
        db.commit()
        
        return result
    
    # Call external AI detection API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.AI_DETECTOR_API_URL}/detect",
                json={"text": request.input_text}
            )
            response.raise_for_status()
            processing_time = time.time() - start_time
            
            # Update log entry with response information
            log_entry.processing_time = processing_time
            log_entry.status_code = 200
            
            # Update usage statistics
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
                    user_id=current_user.id,
                    year=today.year,
                    month=today.month,
                    day=today.day,
                    detect_requests=1,
                    words_processed=word_count,
                    total_processing_time=processing_time
                )
                db.add(new_usage_stat)
            
            db.commit()
            
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error calling AI detector API: {str(e)}")
            log_entry.error = str(e)
            log_entry.status_code = 503
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error connecting to AI detection service"
            )

# M-Pesa Payment Integration
@app.post("/api/payments/mpesa/initiate", response_model=schemas.MpesaPaymentResponse)
async def initiate_mpesa_payment(
    payment_request: schemas.MpesaPaymentRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
        import uuid
        checkout_request_id = str(uuid.uuid4())
        
        # Create a transaction record
        transaction = models.Transaction(
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
async def mpesa_callback(
    callback: schemas.MpesaCallback,
    db: Session = Depends(get_db)
):
    # This would process the callback from M-Pesa after payment
    
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

# Simulate a payment for testing (in real environment, this would be removed)
@app.post("/api/payments/simulate", response_model=schemas.Transaction)
async def simulate_payment(
    amount: float,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Create a transaction record
    transaction = models.Transaction(
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

# Health Check Endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Check database connection
    try:
        # Simple query to verify database connection
        db.execute(text("SELECT 1"))
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
    env_info = {}
    
    # List of environment variables to include (without sensitive values)
    env_vars_to_show = [
        "RAILWAY_PROJECT_NAME", 
        "RAILWAY_SERVICE_NAME", 
        "RAILWAY_ENVIRONMENT_NAME",
        "RAILWAY_PUBLIC_DOMAIN",
        "HUMANIZER_API_URL"
    ]
    
    for var in env_vars_to_show:
        env_info[var] = os.getenv(var, "Not set")
    
    # Add database type info
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        db_type = db_url.split(":")[0]
        db_info = f"{db_type} database"
        if "@" in db_url:
            host = db_url.split("@")[1].split("/")[0]
            db_info += f" at {host}"
        env_info["DATABASE_TYPE"] = db_info
    
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": "Backend API Gateway for Andikar AI services",
        "status": "up and running",
        "environment": env_info,
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "health_check": "/health",
        "admin_dashboard": "/admin"
    }

# Include admin routes
app.include_router(admin_router)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting {settings.PROJECT_NAME} server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
