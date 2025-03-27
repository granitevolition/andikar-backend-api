# Keep the full file content and add a test route
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
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import text, desc, func
from sqlalchemy.orm import Session  # Added missing Session import
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
PROJECT_VERSION = "1.0.2"
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
HUMANIZER_API_URL = os.getenv("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
AI_DETECTOR_API_URL = os.getenv("AI_DETECTOR_API_URL", "https://ai-detector-api.example.com")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # 1 hour in seconds

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

# Database setup
try:
    # Import database modules
    from database import get_db, engine, init_db
    import models
    from models import Base, User as UserModel, PricingPlan, Transaction as TransactionModel
    
    # Initialize database (create tables if needed)
    if engine:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
    else:
        logger.error("Database engine not available, some functionality may be limited")
        
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Dummy database function for fallback
    def get_db():
        logger.warning("Using dummy database function")
        yield None
    
    models = None

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
    
    # If templates fail or aren't available, return a basic HTML response
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{PROJECT_NAME}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 1rem;
                color: #333;
                line-height: 1.6;
            }}
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid #eaeaea;
            }}
            .status-indicator {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background-color: #10b981;
                margin-right: 6px;
            }}
            section {{
                margin-bottom: 2rem;
            }}
            h1, h2, h3 {{
                margin-top: 0;
            }}
            ul {{
                padding-left: 20px;
            }}
            .card {{
                background: #f9fafb;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                border: 1px solid #e5e7eb;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .badge {{
                display: inline-block;
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 500;
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
            }}
            .badge-get {{
                background-color: #dbeafe;
                color: #1e40af;
            }}
            .badge-post {{
                background-color: #dcfce7;
                color: #166534;
            }}
            .badge-put {{
                background-color: #fef3c7;
                color: #92400e;
            }}
            footer {{
                margin-top: 3rem;
                padding-top: 1rem;
                border-top: 1px solid #eaeaea;
                text-align: center;
                font-size: 0.875rem;
                color: #6b7280;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            code {{
                background-color: #f3f4f6;
                padding: 0.2rem 0.4rem;
                border-radius: 4px;
                font-size: 0.875rem;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            }}
        </style>
    </head>
    <body>
        <header>
            <div>
                <h1>{PROJECT_NAME}</h1>
                <p>Version {PROJECT_VERSION}</p>
            </div>
            <div>
                <span><span class="status-indicator"></span> System: Healthy</span>
            </div>
        </header>
        
        <section>
            <h2>Quick Access</h2>
            <div class="grid">
                <a href="/" class="card">
                    <h3>Home Page</h3>
                    <p>Main index and dashboard</p>
                </a>
                <a href="/admin" class="card">
                    <h3>Admin Dashboard</h3>
                    <p>Administration interface</p>
                </a>
                <a href="/docs" class="card">
                    <h3>API Documentation</h3>
                    <p>Interactive API references</p>
                </a>
                <a href="/health" class="card">
                    <h3>System Health</h3>
                    <p>System status and health checks</p>
                </a>
            </div>
        </section>
        
        <section>
            <h2>Admin Area</h2>
            <ul>
                <li><a href="/admin">Dashboard</a> - Overview and statistics</li>
                <li><a href="/admin/users">User Management</a> - Manage users and permissions</li>
                <li><a href="/admin/transactions">Transaction Management</a> - View payment records</li>
                <li><a href="/admin/logs">API Logs</a> - Monitor API usage and errors</li>
                <li><a href="/admin/settings">System Settings</a> - Configure application settings</li>
            </ul>
        </section>
        
        <section>
            <h2>Documentation</h2>
            <ul>
                <li><a href="/docs">Swagger UI</a> - Interactive API documentation</li>
                <li><a href="/redoc">ReDoc</a> - Alternative API documentation</li>
                <li><a href="/openapi.json">OpenAPI Schema</a> - Raw OpenAPI JSON schema</li>
                <li><a href="/health">Health Status</a> - System health information</li>
            </ul>
        </section>
        
        <section>
            <h2>API Endpoints</h2>
            
            <h3>Authentication & User Management</h3>
            <div>
                <span class="badge badge-post">POST</span><a href="/token">/token</a> - Obtain authentication token
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/users/register">/users/register</a> - Register new user
            </div>
            <div>
                <span class="badge badge-get">GET</span><a href="/users/me">/users/me</a> - Get current user profile
            </div>
            <div>
                <span class="badge badge-put">PUT</span><a href="/users/me">/users/me</a> - Update user profile
            </div>
            
            <h3>Text Services</h3>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/humanize">/api/humanize</a> - Humanize text content
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/detect">/api/detect</a> - Detect AI-generated content
            </div>
            
            <h3>Payments</h3>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/payments/mpesa/initiate">/api/payments/mpesa/initiate</a> - Initiate M-Pesa payment
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/payments/mpesa/callback">/api/payments/mpesa/callback</a> - M-Pesa callback
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/payments/simulate">/api/payments/simulate</a> - Simulate payment (testing)
            </div>
        </section>
        
        <section>
            <h2>System Information</h2>
            <div class="card">
                <div><strong>API Version:</strong> {PROJECT_VERSION}</div>
                <div><strong>Environment:</strong> {os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")}</div>
                <div><strong>Status:</strong> <span class="status-indicator"></span> Healthy</div>
                <div><strong>Timestamp:</strong> {datetime.utcnow().isoformat()}</div>
            </div>
        </section>
        
        <footer>
            &copy; {datetime.utcnow().year} Andikar. All rights reserved.
        </footer>
    </body>
    </html>
    """)

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
    
    # Database details - only shown in non-production environments
    db_details = {}
    if os.getenv("RAILWAY_ENVIRONMENT_NAME") != "production" and db is not None:
        try:
            # Get database version
            result = db.execute(text("SELECT version()")).scalar()
            db_details["version"] = result
            
            # Get connection info
            result = db.execute(text("SELECT current_database(), current_user")).first()
            if result:
                db_details["database"] = result[0]
                db_details["user"] = result[1]
                
            # Get table counts
            tables = {
                "users": db.query(func.count(models.User.id)).scalar() or 0,
                "transactions": db.query(func.count(models.Transaction.id)).scalar() or 0,
                "api_logs": db.query(func.count(models.APILog.id)).scalar() or 0
            }
            db_details["tables"] = tables
        except Exception as e:
            logger.error(f"Failed to get database details: {str(e)}")
            db_details["error"] = str(e)
    
    return {
        "status": "healthy" if db_status == "healthy" and humanizer_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "humanizer_api": humanizer_status,
            "api": "healthy"
        },
        "database_details": db_details if db_details else None,
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production"),
        "api_version": PROJECT_VERSION
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
        # Try to find any active plan
        plan = db.query(models.PricingPlan).filter(models.PricingPlan.is_active == True).first()
        
        if not plan:
            # Create a free plan if no plans exist
            plan = models.PricingPlan(
                id="free",
                name="Free",
                description="Basic access to the API",
                price=0.0,
                word_limit=1000,
                requests_per_day=10,
                features=["Basic text humanization", "Limited requests"],
                is_active=True
            )
            db.add(plan)
            db.commit()
            
        user.plan_id = plan.id
    
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
            
            if response.status_code != 200:
                # Try the echo endpoint as fallback
                logger.warning(f"Humanizer API returned status {response.status_code}, trying echo endpoint")
                response = await client.post(
                    f"{HUMANIZER_API_URL}/echo_text",
                    json={"input_text": request.input_text},
                    timeout=30.0
                )
            
            response.raise_for_status()
            result_data = response.json()
            humanized_text = result_data.get("result", "")
            
            if not humanized_text:
                raise ValueError("Empty response from humanizer API")
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

# Test endpoint to verify template rendering
@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """
    Test page to verify template rendering
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    return templates.TemplateResponse("test.html", {
        "request": request,
        "title": "Test Page"
    })

# Direct admin access without authentication (for testing purposes)
@app.get("/admin-test", response_class=HTMLResponse)
async def admin_test(request: Request):
    """
    Test route for admin dashboard without authentication
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Create a mock user for testing
    mock_user = {
        "username": "admin",
        "email": "admin@example.com",
        "id": "test-id"
    }
    
    # Minimal stats for displaying the template
    stats = {
        "users": {
            "total": 10,
            "active": 8,
            "recent": []
        },
        "transactions": {
            "successful": 5,
            "pending": 2,
            "total": 7
        },
        "api": {
            "total_requests": 100,
            "humanize_requests": 80,
            "detect_requests": 20
        }
    }
    
    # Simple mock chart data
    charts = {
        "daily_users": json.dumps([{"date": "2025-03-01", "count": 1}, {"date": "2025-03-02", "count": 2}]),
        "daily_api_usage": json.dumps([{"date": "2025-03-01", "humanize": 5, "detect": 2}, {"date": "2025-03-02", "humanize": 6, "detect": 3}])
    }
    
    # System status
    system = {
        "database": "healthy",
        "humanizer": "healthy",
        "detector": "not_configured",
        "mpesa": "healthy",
        "info": {
            "version": PROJECT_VERSION,
            "python_env": "production",
            "railway_project": "Not on Railway",
            "railway_service": "Not on Railway"
        }
    }
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "title": "Admin Dashboard (Test)",
        "user": mock_user,
        "active_page": "dashboard",
        "stats": stats,
        "charts": charts,
        "system": system
    })

# Add Admin routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """
    Admin dashboard index page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Prepare dashboard stats
    stats = {}
    
    # User stats
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar() or 0
    
    # Get recent users
    recent_users = db.query(models.User).order_by(desc(models.User.joined_date)).limit(5).all()
    
    stats["users"] = {
        "total": total_users,
        "active": active_users,
        "recent": recent_users
    }
    
    # Transaction stats
    successful_payments = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    
    pending_payments = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.status == "pending"
    ).scalar() or 0
    
    stats["transactions"] = {
        "successful": successful_payments,
        "pending": pending_payments,
        "total": successful_payments + pending_payments
    }
    
    # API stats
    total_requests = db.query(func.count(models.APILog.id)).scalar() or 0
    humanize_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/humanize"
    ).scalar() or 0
    detect_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/detect"
    ).scalar() or 0
    
    stats["api"] = {
        "total_requests": total_requests,
        "humanize_requests": humanize_requests,
        "detect_requests": detect_requests
    }
    
    # Chart data - Daily users
    days = 30
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days-1)
    
    daily_users = []
    daily_api_usage = []
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Count users joined on this date
        user_count = db.query(func.count(models.User.id)).filter(
            func.cast(models.User.joined_date, db.Date) == current_date
        ).scalar() or 0
        
        daily_users.append({
            "date": date_str,
            "count": user_count
        })
        
        # Count API requests on this date
        humanize_count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == "/api/humanize",
            func.cast(models.APILog.timestamp, db.Date) == current_date
        ).scalar() or 0
        
        detect_count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == "/api/detect",
            func.cast(models.APILog.timestamp, db.Date) == current_date
        ).scalar() or 0
        
        daily_api_usage.append({
            "date": date_str,
            "humanize": humanize_count,
            "detect": detect_count
        })
    
    charts = {
        "daily_users": json.dumps(daily_users),
        "daily_api_usage": json.dumps(daily_api_usage)
    }
    
    # System status
    system = {}
    
    # Check DB status
    try:
        db.execute(text("SELECT 1"))
        system["database"] = "healthy"
    except Exception:
        system["database"] = "unhealthy"
    
    # Check Humanizer API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HUMANIZER_API_URL}/", timeout=2.0)
            system["humanizer"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        system["humanizer"] = "unhealthy"
    
    # Check AI Detector (simulated)
    system["detector"] = "not_configured"
    
    # Check M-Pesa (simulated)
    system["mpesa"] = "healthy"
    
    # System info
    system["info"] = {
        "version": PROJECT_VERSION,
        "python_env": os.environ.get("PYTHON_ENV", "production"),
        "railway_project": os.environ.get("RAILWAY_PROJECT_NAME", "Not on Railway"),
        "railway_service": os.environ.get("RAILWAY_SERVICE_NAME", "Not on Railway")
    }
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "title": "Admin Dashboard",
        "user": current_user,
        "active_page": "dashboard",
        "stats": stats,
        "charts": charts,
        "system": system
    })

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request, 
    page: int = 1,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    User management page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Get users with pagination
    page_size = 10
    offset = (page - 1) * page_size
    
    users = db.query(models.User).offset(offset).limit(page_size).all()
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_pages = (total_users + page_size - 1) // page_size
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "title": "User Management",
        "users": users,
        "page": page,
        "total_pages": total_pages,
        "total_users": total_users,
        "active_page": "users",
        "user": current_user
    })

@app.get("/admin/user/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    user_id: str,
    request: Request,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    User detail page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Get user details
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's plan
    plan = db.query(models.PricingPlan).filter(models.PricingPlan.id == user.plan_id).first()
    
    # Get user's transactions
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(desc(models.Transaction.created_at)).all()
    
    # Get usage stats
    usage_stats = db.query(models.UsageStat).filter(
        models.UsageStat.user_id == user_id
    ).order_by(
        desc(models.UsageStat.year),
        desc(models.UsageStat.month),
        desc(models.UsageStat.day)
    ).limit(30).all()
    
    return templates.TemplateResponse("admin/user_detail.html", {
        "request": request,
        "title": f"User: {user.username}",
        "selected_user": user,
        "plan": plan,
        "transactions": transactions,
        "usage_stats": usage_stats,
        "active_page": "users",
        "user": current_user
    })

@app.get("/admin/create-user", response_class=HTMLResponse)
async def admin_create_user_form(
    request: Request,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    User creation form
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Get available plans
    plans = db.query(models.PricingPlan).filter(models.PricingPlan.is_active == True).all()
    
    return templates.TemplateResponse("admin/create_user.html", {
        "request": request,
        "title": "Create User",
        "plans": plans,
        "active_page": "users",
        "user": current_user
    })

@app.post("/admin/create-user")
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None),
    plan_id: str = Form(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user from admin dashboard
    """
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(password)
    
    new_user = models.User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        plan_id=plan_id,
        payment_status="Paid",  # Admin-created users are set to paid by default
        words_used=0,
        joined_date=datetime.utcnow(),
        api_keys={},
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    
    # Redirect to the users list
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/transactions", response_class=HTMLResponse)
async def admin_transactions(
    request: Request,
    page: int = 1,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Transaction management page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Get transactions with pagination
    page_size = 20
    offset = (page - 1) * page_size
    
    transactions = db.query(models.Transaction).order_by(
        desc(models.Transaction.created_at)
    ).offset(offset).limit(page_size).all()
    
    total_transactions = db.query(func.count(models.Transaction.id)).scalar() or 0
    total_pages = (total_transactions + page_size - 1) // page_size
    
    # Fetch usernames for transactions
    transaction_data = []
    for tx in transactions:
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()
        username = user.username if user else "Unknown"
        
        transaction_data.append({
            "id": tx.id,
            "short_id": tx.id[:8] + "...",
            "username": username,
            "user_id": tx.user_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "payment_method": tx.payment_method,
            "status": tx.status,
            "created_at": tx.created_at
        })
    
    return templates.TemplateResponse("admin/transactions.html", {
        "request": request,
        "title": "Transaction Management",
        "transactions": transaction_data,
        "page": page,
        "total_pages": total_pages,
        "total_transactions": total_transactions,
        "active_page": "transactions",
        "user": current_user
    })

@app.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    page: int = 1,
    endpoint: Optional[str] = None,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    API logs page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Get logs with pagination and filtering
    page_size = 50
    offset = (page - 1) * page_size
    
    query = db.query(models.APILog)
    if endpoint:
        query = query.filter(models.APILog.endpoint == endpoint)
    
    logs = query.order_by(desc(models.APILog.timestamp)).offset(offset).limit(page_size).all()
    
    total_query = db.query(func.count(models.APILog.id))
    if endpoint:
        total_query = total_query.filter(models.APILog.endpoint == endpoint)
    
    total_logs = total_query.scalar() or 0
    total_pages = (total_logs + page_size - 1) // page_size
    
    # Get unique endpoints for filtering
    endpoints = db.query(models.APILog.endpoint).distinct().all()
    endpoint_list = [ep[0] for ep in endpoints]
    
    return templates.TemplateResponse("admin/logs.html", {
        "request": request,
        "title": "API Logs",
        "logs": logs,
        "page": page,
        "total_pages": total_pages,
        "total_logs": total_logs,
        "endpoints": endpoint_list,
        "selected_endpoint": endpoint,
        "active_page": "logs",
        "user": current_user
    })

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    System settings page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Get pricing plans
    plans = db.query(models.PricingPlan).all()
    
    # Get environment variables and configuration
    config = {
        "PROJECT_NAME": PROJECT_NAME,
        "PROJECT_VERSION": PROJECT_VERSION,
        "HUMANIZER_API_URL": HUMANIZER_API_URL,
        "AI_DETECTOR_API_URL": AI_DETECTOR_API_URL,
        "RATE_LIMIT_REQUESTS": RATE_LIMIT_REQUESTS,
        "RATE_LIMIT_PERIOD": RATE_LIMIT_PERIOD,
        "ACCESS_TOKEN_EXPIRE_MINUTES": ACCESS_TOKEN_EXPIRE_MINUTES,
        "ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")
    }
    
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "title": "System Settings",
        "plans": plans,
        "config": config,
        "active_page": "settings",
        "user": current_user
    })

# Database admin routes
@app.get("/admin/database/reset")
async def reset_database(
    confirm: str = "no",
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    if confirm.lower() != "yes":
        return {
            "message": "Database reset requires confirmation",
            "instructions": "Add ?confirm=yes to the URL to confirm reset"
        }
        
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        # Create tables again
        Base.metadata.create_all(bind=engine)
        # Initialize the database
        init_db()
        
        return {
            "status": "success",
            "message": "Database has been reset successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting database: {str(e)}"
        )

# Admin data seeding route
@app.post("/admin/database/seed")
async def seed_database(
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        # Initialize the database with seed data
        if init_db():
            return {
                "status": "success",
                "message": "Database has been seeded successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database seeding failed"
            )
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error seeding database: {str(e)}"
        )

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting {PROJECT_NAME} server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
