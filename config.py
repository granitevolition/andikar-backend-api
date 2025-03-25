import os
from datetime import timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    # Project information
    PROJECT_NAME: str = "Andikar Backend API"
    PROJECT_VERSION: str = "1.0.6"
    
    # JWT Settings
    SECRET_KEY: str = "mysecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Service API Endpoints
    HUMANIZER_API_URL: str = "https://web-production-3db6c.up.railway.app"
    AI_DETECTOR_API_URL: str = "https://ai-detector-api.example.com"
    
    # M-Pesa Settings
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_CALLBACK_URL: str = ""
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # in seconds
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Create instance of settings
settings = Settings()
