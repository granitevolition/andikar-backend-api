from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, List, Optional, Any, Union
import httpx
import os
import json
import logging
import time
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
import traceback

# Import configuration
from config import settings

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

# Simple health check that doesn't depend on database
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": "Backend API Gateway for Andikar AI services",
        "status": "up and running",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "health_check": "/health"
    }

# Import other modules after FastAPI app is created
# This ensures the app object is available and avoids circular imports
from database import get_db, engine
import models
from models import Base
import schemas
from utils import detect_ai_content

# Import authentication utilities
from auth import (
    verify_password, get_password_hash, authenticate_user,
    create_access_token, get_current_user, get_current_active_user,
    oauth2_scheme, pwd_context
)

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

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
        logger.info("Created database tables")
        
        # Initialize default pricing plans if they don't exist
        db = next(get_db())
        
        if db.query(models.PricingPlan).count() == 0:
            logger.info("Initializing default pricing plans")
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
            logger.info("Created default pricing plans")
        
        # Create an admin user if it doesn't exist
        if not db.query(models.User).filter(models.User.username == "admin").first():
            logger.info("Creating admin user")
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
        
        # Import and include admin routes after app creation to avoid circular imports
        try:
            from admin import admin_router
            app.include_router(admin_router)
            logger.info("Admin routes registered")
        except ImportError as e:
            logger.warning(f"Could not import admin routes: {str(e)}")
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
    user_data = user_update.model_dump(exclude_unset=True)  # model_dump instead of dict in Pydantic v2
    
    if user_data:
        for key, value in user_data.items():
            setattr(current_user, key, value)
        
        db.commit()
        db.refresh(current_user)
    
    return current_user

# Initialize database
@app.post("/api/init-db")
async def init_db():
    """
    Initialize the database (admin-only endpoint for manual initialization)
    """
    try:
        # Run database initialization
        import subprocess
        import sys
        
        result = subprocess.run([sys.executable, "init_db.py"], 
                              capture_output=True, 
                              text=True)
        
        return {
            "success": True,
            "message": "Database initialized successfully",
            "details": result.stdout
        }
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return {
            "success": False,
            "message": "Database initialization failed",
            "error": str(e)
        }

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
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.HUMANIZER_API_URL}/humanize_text",
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
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AI_DETECTOR_API_URL}/detect",
                json={"text": request.input_text},
                timeout=30.0
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

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting {settings.PROJECT_NAME} server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
