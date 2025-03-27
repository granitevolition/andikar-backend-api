"""
Database connection utilities for Andikar Backend API.
Provides SQLAlchemy engine and session management.
"""
import os
import logging
import time
import socket
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
        s.connect((host, port))
        s.close()
        return True
    except Exception as e:
        logger.warning(f"Host {host}:{port} is not reachable: {str(e)}")
        return False

def get_database_url():
    """
    Determine the most appropriate database URL to use.
    Tries multiple approaches based on Railway's deployment model.
    """
    # Option 1: Use fully formed DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if "postgres:" in database_url:
            database_url = database_url.replace("postgres:", "postgresql:")
        logger.info(f"Using DATABASE_URL from environment variable")
        return database_url

    # Option 2: Try internal Railway networking
    pg_host = os.getenv("RAILWAY_PRIVATE_DOMAIN", "postgres.railway.internal")
    pg_port = 5432
    if check_host_connectivity(pg_host, pg_port):
        pg_user = os.getenv("PGUSER", "postgres")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "")
        pg_db = os.getenv("PGDATABASE", "railway")
        
        database_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        logger.info(f"Using internal Railway PostgreSQL connection")
        return database_url

    # Option 3: Use externally accessible DATABASE_PUBLIC_URL
    database_public_url = os.getenv("DATABASE_PUBLIC_URL")
    if database_public_url:
        if "postgres:" in database_public_url:
            database_public_url = database_public_url.replace("postgres:", "postgresql:")
        logger.info(f"Using DATABASE_PUBLIC_URL from environment variable")
        return database_public_url

    # Option 4: Construct external URL from environment variables
    pg_public_host = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    pg_public_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    
    if pg_public_host and pg_public_port:
        pg_user = os.getenv("PGUSER", "postgres")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "")
        pg_db = os.getenv("PGDATABASE", "railway")
        
        database_url = f"postgresql://{pg_user}:{pg_pass}@{pg_public_host}:{pg_public_port}/{pg_db}"
        logger.info(f"Using constructed public PostgreSQL connection")
        return database_url

    # Option 5: Fallback to SQLite for local development
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
                engine = create_engine(
                    SQLALCHEMY_DATABASE_URL,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    echo=False,
                    connect_args={
                        "connect_timeout": 10,  # Timeout for connection establishment
                        "application_name": "andikar-backend-api"  # Helps identify connections in pg_stat_activity
                    }
                )
                
                # Test connection
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1")).fetchone()
                    if result and result[0] == 1:
                        logger.info(f"Successfully connected to database (attempt {attempt+1})")
                        return engine
                    
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt+1} failed: {str(e)}")
                
                if attempt < max_attempts - 1:
                    backoff = min(2 ** attempt, 30)  # Exponential backoff capped at 30 seconds
                    logger.info(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                else:
                    logger.error(f"All {max_attempts} database connection attempts failed")
        
        # If we get here, all connection attempts failed
        logger.error("Could not establish database connection, returning None")
        return None

# Create the engine
engine = create_db_engine()

# Create session class
if engine is not None:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database session maker created successfully")
else:
    # Dummy SessionLocal that will raise exceptions if used
    logger.warning("Creating dummy SessionLocal due to database connection failure")
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
