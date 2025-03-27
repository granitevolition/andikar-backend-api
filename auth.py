"""
Authentication utilities for Andikar Backend API.

This module provides all authentication-related functionality including:
- Password hashing and verification
- JWT token generation and validation
- User authentication functions
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import logging

# Import configuration
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Set up logging
logger = logging.getLogger("andikar-auth")

# Initialize password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models for token data
class TokenData(BaseModel):
    username: Optional[str] = None

# Password utilities
def verify_password(plain_password, hashed_password):
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Generate a password hash"""
    return pwd_context.hash(password)

# User authentication
def authenticate_user(db, username: str, password: str):
    """Authenticate a user by username and password"""
    if db is None:
        logger.warning("Database connection unavailable during authentication")
        return None
    
    # Dynamic import to avoid circular dependencies
    from models import User
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"Authentication failed: User '{username}' not found")
        return None
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed: Invalid password for user '{username}'")
        return None
    
    logger.info(f"Authentication successful for user: {username}")
    return user

# JWT token handling
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token with expiration"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

# User dependency functions
async def get_current_user(token: str = Depends(oauth2_scheme), db = None):
    """Get the current user from a JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if db is None:
        # Dynamic import to avoid circular dependencies
        from database import get_db
        db = next(get_db())
    
    if db is None:
        logger.error("Database unavailable during token validation")
        raise credentials_exception
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            logger.warning("Token validation failed: No username in token payload")
            raise credentials_exception
            
        token_data = TokenData(username=username)
    except JWTError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise credentials_exception
    
    # Get user from database
    from models import User
    user = db.query(User).filter(User.username == token_data.username).first()
    
    if user is None:
        logger.warning(f"Token validation failed: User '{token_data.username}' not found")
        raise credentials_exception
        
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Check if the current user is active"""
    if not current_user.is_active:
        logger.warning(f"Access attempt by inactive user: {current_user.username}")
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user = Depends(get_current_user)):
    """Check if the current user is an admin"""
    # For now, we just check if the user is the admin user
    if current_user.username != "admin":
        logger.warning(f"Unauthorized admin access attempt by user: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access admin area"
        )
    return current_user
