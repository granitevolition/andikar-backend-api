import os
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("andikar-database")

# Create base class for SQLAlchemy models
Base = declarative_base()

def get_database_url():
    """Get the database URL from environment variables."""
    # Priority 1: Use the direct DATABASE_URL if available
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Convert postgres:// to postgresql:// if needed
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        logger.info(f"Using DATABASE_URL from environment")
        return db_url

    # Priority 2: Construct from proxy variables
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("PGDATABASE", "railway")
    
    if proxy_domain and proxy_port and password:
        # Use quote_plus to properly encode the password
        encoded_password = quote_plus(password)
        db_url = f"postgresql://{user}:{encoded_password}@{proxy_domain}:{proxy_port}/{db}"
        logger.info(f"Using Railway TCP proxy connection: {proxy_domain}:{proxy_port}")
        return db_url
    
    # No PostgreSQL connection available
    return None

def create_db_engine(max_attempts=5, retry_interval=2):
    """Create database engine with retry logic."""
    database_url = get_database_url()
    
    if not database_url:
        logger.error("No PostgreSQL connection configuration found")
        logger.warning("⚠️ Creating SQLite fallback engine - FOR DEVELOPMENT ONLY")
        return create_engine("sqlite:///andikar.db")
    
    # Mask password in logs
    safe_url = database_url
    if os.getenv("PGPASSWORD"):
        safe_url = safe_url.replace(os.getenv("PGPASSWORD", ""), "*" * 8)
    if os.getenv("POSTGRES_PASSWORD"):
        safe_url = safe_url.replace(os.getenv("POSTGRES_PASSWORD", ""), "*" * 8)
    logger.info(f"Database URL: {safe_url}")
    
    # Try to connect to the database with retries
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt}/{max_attempts})...")
            engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "andikar_backend_api"
                }
            )
            engine.connect().close()  # Test connection
            logger.info("✅ Database connection successful!")
            return engine
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                backoff = 2 ** (attempt - 1)
                logger.info(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                logger.error(f"❌ All {max_attempts} database connection attempts failed")
                logger.error(f"Last connection error: {e}")
                logger.warning("⚠️ Creating SQLite fallback engine - FOR DEVELOPMENT ONLY")
                return create_engine("sqlite:///andikar.db")

# Create engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database with seed data.
    
    This function is called during application startup to ensure
    that necessary tables and seed data exist in the database.
    Returns True if successful, False otherwise.
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Import models here to avoid circular imports
        from models import User, PricingPlan
        
        # Create session for seeding
        with SessionLocal() as db:
            # Check if we need to create pricing plans
            plan_count = db.query(PricingPlan).count()
            if plan_count == 0:
                logger.info("Creating default pricing plans...")
                
                # Create default pricing plans
                plans = [
                    PricingPlan(
                        id="free",
                        name="Free",
                        description="Basic plan with limited usage",
                        price=0.0,
                        word_limit=1000,
                        requests_per_day=10,
                        features=["Basic text humanization"],
                        is_active=True
                    ),
                    PricingPlan(
                        id="basic",
                        name="Basic",
                        description="Standard plan for regular users",
                        price=9.99,
                        word_limit=10000,
                        requests_per_day=100,
                        features=["Advanced text humanization", "AI detection"],
                        is_active=True
                    ),
                    PricingPlan(
                        id="pro",
                        name="Professional",
                        description="Advanced plan for professional users",
                        price=29.99,
                        word_limit=50000,
                        requests_per_day=500,
                        features=["Premium text humanization", "Advanced AI detection", "Priority support"],
                        is_active=True
                    )
                ]
                
                db.add_all(plans)
                db.commit()
                logger.info("Default pricing plans created")
                
            # Check if we need to create admin user
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                logger.info("Creating admin user...")
                
                # Import bcrypt here to avoid circular imports
                import bcrypt
                
                # Create admin user with default password
                password = "admin123"
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                admin = User(
                    username="admin",
                    email="admin@andikar.com",
                    full_name="Admin User",
                    hashed_password=hashed_password,
                    plan_id="pro",
                    words_used=0,
                    payment_status="Paid",
                    is_active=True
                )
                
                db.add(admin)
                db.commit()
                logger.info("Admin user created")
                
        logger.info("Database initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
