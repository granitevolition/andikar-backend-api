"""
Configuration module for Andikar Backend API.

This module contains all application settings and configuration variables.
It centralizes settings to avoid duplication and ensure consistent configuration
across the application.

Version: 1.0.6
Author: Andikar Team
"""

import os
from datetime import timedelta
from pydantic import BaseSettings

class Settings:
    # Application information
    PROJECT_NAME = "Andikar Backend API"
    PROJECT_VERSION = "1.0.6"
    
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

# Create instance of settings to be imported by other modules
settings = Settings()
