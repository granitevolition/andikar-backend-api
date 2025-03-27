"""
Database connection utilities for Andikar Backend API.
Provides SQLAlchemy engine and session management.
"""
import os
import logging
import time
import socket
import json
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("andikar-database")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Improved connection strategy for better reliability
def check_host_connectivity(host, port, timeout=3):
    """Check if a host is reachable on the given port."""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.close()
        logger.info(f"✅ Host {host}:{port} is reachable")
        return True
    except Exception as e:
        logger.warning(f"Host {host}:{port} is not reachable: {str(e)}")
        return False

def get_database_url():
    """
    Determine the most appropriate database URL to use.
    Prioritizes the exact DATABASE_URL from the environment.
    """
    # Priority 1: Use exact DATABASE_URL from environment (most reliable)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Ensure it's using postgresql:// protocol
        if database_url.startswith("postgres:"):
            database_url = database_url.replace("postgres:", "postgresql:")
        logger.info("Using exact DATABASE_URL from environment variable")
        return database_url
    
    # Priority 2: Construct from TCP proxy details
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    pg_user = os.getenv("PGUSER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("PGDATABASE", "railway")
    
    if proxy_domain and proxy_port and pg_password:
        proxy_conn_string = f"postgresql://{pg_user}:{pg_password}@{proxy_domain}:{proxy_port}/{pg_db}"
        logger.info(f"Using TCP proxy connection: postgresql://{pg_user}:****@{proxy_domain}:{proxy_port}/{pg_db}")
        return proxy_conn_string
    
    # Priority 3: Try direct internal connection
    pg_host = os.getenv("PGHOST", "postgres.railway.internal")
    pg_port = os.getenv("PGPORT", "5432")
    
    if pg_host and pg_port and pg_password:
        direct_conn_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
        logger.info(f"Using direct internal connection: postgresql://{pg_user}:****@{pg_host}:{pg_port}/{pg_db}")
        return direct_conn_string
    
    # If all else fails, use SQLite as fallback (development only)
    logger.warning("No PostgreSQL connection configuration found, using SQLite fallback")
    return "sqlite:///./andikar.db"

# Get the appropriate database URL
SQLALCHEMY_DATABASE_URL = get_database_url()
    
# Display truncated connection string (hide credentials)
def safe_db_url(url):
    if '@' in url:
        parts = url.split('@')
        auth_part = parts[0].split('://')
        return f"{auth_part[0]}://*****@{parts[1]}"
    return url

logger.info(f"Database URL: {safe_db_url(SQLALCHEMY_DATABASE_URL)}")

# Create engine with appropriate configuration
def create_db_engine():
    """Create database engine with appropriate retry logic and configuration."""
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        # SQLite-specific configuration
        logger.warning("⚠️ Using SQLite as fallback - THIS SHOULD NOT HAPPEN IN PRODUCTION")
        return create_engine(
            SQLALCHEMY_DATABASE_URL, 
            connect_args={"check_same_thread": False},
            echo=False
        )
    else:
        # PostgreSQL configuration with retry logic
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempting to connect to database (attempt {attempt+1}/{max_attempts})...")
                
                engine = create_engine(
                    SQLALCHEMY_DATABASE_URL,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    echo=False,
                    connect_args={
                        "connect_timeout": 15,  # Increased timeout for connection establishment
                        "application_name": "andikar-backend-api"
                    }
                )
                
                # Test connection
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1")).fetchone()
                    if result and result[0] == 1:
                        logger.info(f"✅ Successfully connected to database (attempt {attempt+1})")
                        
                        # Print database details for debugging
                        try:
                            version = conn.execute(text("SELECT version()")).scalar()
                            logger.info(f"PostgreSQL version: {version}")
                            
                            db_info = conn.execute(text("SELECT current_database(), current_user")).fetchone()
                            if db_info:
                                logger.info(f"Database: {db_info[0]}, User: {db_info[1]}")
                        except Exception as e:
                            logger.warning(f"Could not get database details: {e}")
                            
                        return engine
                    
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt+1} failed: {str(e)}")
                
                if attempt < max_attempts - 1:
                    backoff = min(2 ** attempt, 30)  # Exponential backoff capped at 30 seconds
                    logger.info(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                else:
                    logger.error(f"❌ All {max_attempts} database connection attempts failed")
                    logger.error(f"Last connection error: {str(e)}")
                    
                    # Instead of returning None, create a SQLite fallback as absolute last resort
                    logger.warning("⚠️ Creating SQLite fallback engine - FOR DEVELOPMENT ONLY")
                    sqlite_url = "sqlite:///./andikar_fallback.db"
                    return create_engine(
                        sqlite_url,
                        connect_args={"check_same_thread": False},
                        echo=False
                    )
        
        # This should never be reached, but just in case
        logger.error("Could not establish any database connection")
        return None

# Create the engine
engine = create_db_engine()

# Create session class
if engine is not None:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database session maker created successfully")
else:
    # Dummy SessionLocal that will raise exceptions if used
    logger.error("❌ CRITICAL: Failed to create database engine")
    SessionLocal = None

# Create Base class for models
Base = declarative_base()

# Dependency to get a database session
def get_db():
    """FastAPI dependency that provides a database session."""
    if SessionLocal is None:
        logger.error("Attempted to get database session but no connection available")
        yield None
        return
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to initialize the database
def init_db():
    """Initialize database tables and seed data."""
    if engine is None:
        logger.error("Cannot initialize database, no connection available")
        return False
    
    try:
        # Import models to ensure they're registered with Base
        from models import Base, PricingPlan, User
        import uuid
        from passlib.context import CryptContext
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")
        
        # Seed initial data
        with SessionLocal() as db:
            # Check if we need to seed pricing plans
            if db.query(PricingPlan).count() == 0:
                logger.info("Seeding pricing plans")
                
                # Create pricing plans
                free_plan = PricingPlan(
                    id="free",
                    name="Free",
                    description="Basic access to the API",
                    price=0.0,
                    word_limit=1000,
                    requests_per_day=10,
                    features=["Basic text humanization", "Limited requests"]
                )
                
                standard_plan = PricingPlan(
                    id="standard",
                    name="Standard",
                    description="Standard access with higher limits",
                    price=9.99,
                    word_limit=10000,
                    requests_per_day=100,
                    features=["Full text humanization", "AI detection", "Higher word limits"]
                )
                
                premium_plan = PricingPlan(
                    id="premium",
                    name="Premium",
                    description="Premium access with highest limits",
                    price=29.99,
                    word_limit=100000,
                    requests_per_day=1000,
                    features=["Priority processing", "Advanced humanization", "Unlimited detections", "Technical support"]
                )
                
                db.add_all([free_plan, standard_plan, premium_plan])
                db.commit()
                logger.info("Pricing plans seeded")
            
            # Check if we need to create an admin user
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            if not db.query(User).filter(User.username == admin_username).first():
                logger.info(f"Creating admin user '{admin_username}'")
                
                # Generate password hash
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                admin_password = os.getenv("ADMIN_PASSWORD", "adminpassword")
                hashed_password = pwd_context.hash(admin_password)
                
                # Create admin user
                admin_user = User(
                    id=str(uuid.uuid4()),
                    username=admin_username,
                    email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
                    full_name="Administrator",
                    hashed_password=hashed_password,
                    plan_id="premium",
                    payment_status="Paid",
                    is_active=True
                )
                
                db.add(admin_user)
                db.commit()
                logger.info("Admin user created")
                
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False