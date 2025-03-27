"""
Configuration settings for Andikar Backend API.

This module centralizes all configuration settings for the application,
making it easier to manage environment variables and default values.

Version: 1.0.1
Author: Andikar Team
"""
import os
from datetime import timedelta

# Application information
PROJECT_NAME = "Andikar Backend API"
PROJECT_VERSION = "1.0.1"

# Environment
DEBUG = os.getenv("DEBUG", "0") == "1"
ENV = os.getenv("ENV", "production")

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# External API endpoints
HUMANIZER_API_URL = os.getenv("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
AI_DETECTOR_API_URL = os.getenv("AI_DETECTOR_API_URL", "https://ai-detector-api.example.com")

# M-Pesa API credentials
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "")

# Rate limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # 1 hour in seconds

# Pricing plans (default values used if not in database)
DEFAULT_PRICING_PLANS = {
    "free": {
        "name": "Free",
        "description": "Basic features for trying out the service",
        "price": 0,
        "word_limit": 500,
        "requests_per_day": 10,
        "features": ["Humanize text (limited)", "AI detection (limited)"]
    },
    "basic": {
        "name": "Basic",
        "description": "Standard features for regular users",
        "price": 500,
        "word_limit": 1500,
        "requests_per_day": 50,
        "features": ["Humanize text", "AI detection", "Email support"]
    },
    "premium": {
        "name": "Premium",
        "description": "Advanced features for professional users",
        "price": 2000,
        "word_limit": 8000,
        "requests_per_day": 100,
        "features": ["Humanize text", "AI detection", "Priority support", "API access"]
    }
}

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_EMAIL = "admin@andikar.com"
