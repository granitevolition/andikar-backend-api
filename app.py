from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import os
import logging
import json
from datetime import datetime, timedelta
from config import settings
from database import get_db, engine
import models
from models import Base
from auth import get_current_active_user, get_current_user, create_access_token, authenticate_user, get_password_hash

# Create app
app = FastAPI(
    title="Andikar Backend API",
    description="API Gateway for Andikar Services",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Root endpoint
@app.get("/")
def read_root():
    return {
        "name": "Andikar Admin API",
        "version": "1.0.0",
        "status": "online",
        "admin": "/admin"
    }

# Auth endpoint
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
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

# Admin dashboard
@app.get("/admin")
async def admin_dashboard(request: Request, current_user: models.User = Depends(get_current_active_user)):
    # Simple template rendering with minimal data
    db = next(get_db())
    user_count = db.query(models.User).count()
    
    return templates.TemplateResponse("admin/simple_dashboard.html", {
        "request": request,
        "user": current_user,
        "user_count": user_count,
        "app_version": settings.PROJECT_VERSION,
        "humanizer_url": settings.HUMANIZER_API_URL
    })

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Initialize database
@app.on_event("startup")
async def startup_event():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create admin user if doesn't exist
    db = next(get_db())
    if not db.query(models.User).filter(models.User.username == "admin").first():
        admin_user = models.User(
            username="admin",
            email="admin@andikar.com",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),
            plan_id="premium",
            payment_status="Paid",
            is_active=True
        )
        db.add(admin_user)
        db.commit()

# Run app
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
