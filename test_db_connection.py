#!/usr/bin/env python3
"""
Database Connection Test Script

This script tests the connection to the PostgreSQL database using direct connection,
SQLAlchemy, and psycopg2. It helps identify connection issues and verify credentials.
"""

import os
import sys
import time
import logging
import urllib.parse
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db-test")

try:
    import psycopg2
    from sqlalchemy import create_engine, text
except ImportError:
    logger.error("Please install required packages: pip install psycopg2-binary sqlalchemy")
    sys.exit(1)

def mask_password(url):
    """Mask the password in a URL for safe logging."""
    if not url:
        return "Not set"
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked = parsed._replace(netloc=parsed.netloc.replace(
                parsed.password, "****"))
            return masked.geturl()
        return url
    except Exception:
        return url

def get_database_url():
    """Get the database URL from environment variables."""
    # Check for DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Convert postgres:// to postgresql:// if needed
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        logger.info(f"Using DATABASE_URL: {mask_password(db_url)}")
        return db_url
    
    # Construct from individual components
    pguser = os.getenv("PGUSER", "postgres")
    pgpassword = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    pgdatabase = os.getenv("PGDATABASE", "railway")
    
    # Try proxy connection
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    
    if proxy_domain and proxy_port and pgpassword:
        # URL encode the password
        encoded_password = urllib.parse.quote_plus(pgpassword)
        db_url = f"postgresql://{pguser}:{encoded_password}@{proxy_domain}:{proxy_port}/{pgdatabase}"
        logger.info(f"Using proxy connection: {mask_password(db_url)}")
        return db_url
    
    # Try direct connection
    pghost = os.getenv("PGHOST", "localhost")
    pgport = os.getenv("PGPORT", "5432")
    
    if pghost and pgport and pgpassword:
        # URL encode the password
        encoded_password = urllib.parse.quote_plus(pgpassword)
        db_url = f"postgresql://{pguser}:{encoded_password}@{pghost}:{pgport}/{pgdatabase}"
        logger.info(f"Using direct connection: {mask_password(db_url)}")
        return db_url
    
    logger.error("No database connection information available")
    return None

def test_sqlalchemy_connection():
    """Test database connection using SQLAlchemy."""
    logger.info("Testing SQLAlchemy connection...")
    
    db_url = get_database_url()
    if not db_url:
        logger.error("Cannot test SQLAlchemy connection: No database URL available")
        return False
    
    try:
        engine = create_engine(
            db_url,
            pool_size=1,
            max_overflow=0,
            connect_args={
                "connect_timeout": 10,
                "application_name": "andikar_connection_test"
            }
        )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            logger.info(f"SQLAlchemy connection successful (test value: {test_value})")
            
            # Get database version
            try:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"Database version: {version}")
            except Exception as e:
                logger.warning(f"Could not get database version: {e}")
            
            # Get current database and user
            try:
                result = conn.execute(text("SELECT current_database(), current_user"))
                db, user = result.fetchone()
                logger.info(f"Connected to database: {db} as user: {user}")
            except Exception as e:
                logger.warning(f"Could not get database/user info: {e}")
        
        return True
    except Exception as e:
        logger.error(f"SQLAlchemy connection failed: {e}")
        return False

def test_psycopg2_connection():
    """Test database connection using psycopg2 directly."""
    logger.info("Testing psycopg2 connection...")
    
    db_url = get_database_url()
    if not db_url:
        logger.error("Cannot test psycopg2 connection: No database URL available")
        return False
    
    try:
        conn = psycopg2.connect(
            db_url,
            connect_timeout=10,
            application_name="andikar_connection_test"
        )
        
        # Test connection
        with conn.cursor() as cur:
            cur.execute("SELECT 1 as test")
            test_value = cur.fetchone()[0]
            logger.info(f"psycopg2 connection successful (test value: {test_value})")
            
            # Get database version
            try:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"Database version: {version}")
            except Exception as e:
                logger.warning(f"Could not get database version: {e}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"psycopg2 connection failed: {e}")
        return False

def main():
    """Run database connection tests."""
    print("\n====== DATABASE CONNECTION TEST ======\n")
    
    # Check environment variables
    print("Environment variables:")
    print(f"DATABASE_URL: {mask_password(os.getenv('DATABASE_URL', 'Not set'))}")
    print(f"PGUSER: {os.getenv('PGUSER', 'Not set')}")
    print(f"PGPASSWORD: {'****' if os.getenv('PGPASSWORD') else 'Not set'}")
    print(f"POSTGRES_PASSWORD: {'****' if os.getenv('POSTGRES_PASSWORD') else 'Not set'}")
    print(f"PGDATABASE: {os.getenv('PGDATABASE', 'Not set')}")
    print(f"PGHOST: {os.getenv('PGHOST', 'Not set')}")
    print(f"PGPORT: {os.getenv('PGPORT', 'Not set')}")
    print(f"RAILWAY_TCP_PROXY_DOMAIN: {os.getenv('RAILWAY_TCP_PROXY_DOMAIN', 'Not set')}")
    print(f"RAILWAY_TCP_PROXY_PORT: {os.getenv('RAILWAY_TCP_PROXY_PORT', 'Not set')}")
    print()
    
    # Test SQLAlchemy connection
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    print()
    
    # Test psycopg2 connection
    psycopg2_ok = test_psycopg2_connection()
    
    print("\n====== CONNECTION TEST RESULTS ======")
    print(f"SQLAlchemy connection: {'✅ SUCCESS' if sqlalchemy_ok else '❌ FAILED'}")
    print(f"psycopg2 connection: {'✅ SUCCESS' if psycopg2_ok else '❌ FAILED'}")
    
    if not sqlalchemy_ok and not psycopg2_ok:
        print("\n❌ All connection methods failed")
        print("Please check your database credentials and connection settings")
        return 1
    else:
        print("\n✅ At least one connection method succeeded")
        print("Database connection is working")
        return 0

if __name__ == "__main__":
    sys.exit(main())
