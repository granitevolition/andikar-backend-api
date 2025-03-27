"""
Database initialization script for Andikar Backend API.
Explicitly creates all database tables and seed data.
Run this script directly to force table creation and seeding.
"""
import os
import sys
import logging
import time
import uuid
from datetime import datetime
from passlib.context import CryptContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-init")

# Import SQLAlchemy components
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base
except ImportError:
    logger.error("SQLAlchemy not installed. Please run: pip install sqlalchemy")
    sys.exit(1)

def get_database_url():
    """Determine the appropriate database URL to use."""
    # Option 1: Use fully formed DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if "postgres:" in database_url:
            database_url = database_url.replace("postgres:", "postgresql:")
        logger.info(f"Using DATABASE_URL from environment variable")
        return database_url

    # Option 2: Use DATABASE_PUBLIC_URL
    database_public_url = os.getenv("DATABASE_PUBLIC_URL")
    if database_public_url:
        if "postgres:" in database_public_url:
            database_public_url = database_public_url.replace("postgres:", "postgresql:")
        logger.info(f"Using DATABASE_PUBLIC_URL from environment variable")
        return database_public_url

    # Option 3: Construct from components
    pg_host = os.getenv("RAILWAY_PRIVATE_DOMAIN") or os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    pg_port = os.getenv("RAILWAY_TCP_PROXY_PORT") or "5432"
    pg_user = os.getenv("PGUSER", "postgres")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "")
    pg_db = os.getenv("PGDATABASE", "railway")
    
    if pg_host:
        database_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        logger.info(f"Using constructed PostgreSQL connection URL")
        return database_url

    # Fallback to SQLite
    logger.warning("No PostgreSQL connection details found. Using SQLite.")
    return "sqlite:///./andikar.db"

def create_engine_and_session(db_url):
    """Create a database engine and session factory."""
    logger.info(f"Creating database engine for: {db_url.split('@')[0]}@...")
    
    # Create engine with appropriate configuration
    if db_url.startswith("sqlite"):
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
    else:
        for attempt in range(5):
            try:
                engine = create_engine(
                    db_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    connect_args={"connect_timeout": 10}
                )
                
                # Test connection
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    logger.info("Database connection successful")
                    break
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt+1}/5 failed: {e}")
                if attempt < 4:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error("All connection attempts failed")
                    raise
    
    # Create session class
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal

def create_tables(engine):
    """Create all database tables."""
    # Create a Base instance
    Base = declarative_base()
    
    # Import models to register them with Base
    from models import User, Transaction, APILog, RateLimit, PricingPlan, Webhook, UsageStat
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")
    
    # Return Base for seed data functions
    return Base

def seed_pricing_plans(session):
    """Seed pricing plan data in the database."""
    from models import PricingPlan
    
    logger.info("Checking for existing pricing plans...")
    existing_plans = session.query(PricingPlan).count()
    
    if existing_plans > 0:
        logger.info(f"Found {existing_plans} existing pricing plans, skipping seeding")
        return
    
    logger.info("Seeding pricing plans...")
    
    # Create free plan
    free_plan = PricingPlan(
        id="free",
        name="Free",
        description="Basic access to the API",
        price=0.0,
        word_limit=1000,
        requests_per_day=10,
        features=["Basic text humanization", "Limited requests"]
    )
    
    # Create standard plan
    standard_plan = PricingPlan(
        id="standard",
        name="Standard",
        description="Standard access with higher limits",
        price=9.99,
        currency="KES",
        word_limit=10000,
        requests_per_day=100,
        features=["Full text humanization", "AI detection", "Higher word limits"]
    )
    
    # Create premium plan
    premium_plan = PricingPlan(
        id="premium",
        name="Premium", 
        description="Premium access with highest limits",
        price=29.99,
        currency="KES",
        word_limit=100000,
        requests_per_day=1000,
        features=["Priority processing", "Advanced humanization", "Unlimited detections", "Technical support"]
    )
    
    # Add plans to session
    session.add_all([free_plan, standard_plan, premium_plan])
    session.commit()
    
    logger.info("Pricing plans seeded successfully")

def create_admin_user(session):
    """Create an admin user if one doesn't exist."""
    from models import User
    
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    
    logger.info(f"Checking for existing admin user '{admin_username}'...")
    existing_admin = session.query(User).filter(User.username == admin_username).first()
    
    if existing_admin:
        logger.info(f"Admin user '{admin_username}' already exists, skipping creation")
        return
    
    logger.info(f"Creating admin user '{admin_username}'...")
    
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
        joined_date=datetime.utcnow(),
        is_active=True
    )
    
    # Add to session
    session.add(admin_user)
    session.commit()
    
    logger.info(f"Admin user '{admin_username}' created successfully")

def main():
    """Main initialization function."""
    print("=" * 60)
    print("Andikar Backend API - Database Initialization")
    print("=" * 60)
    
    try:
        # Get database URL
        db_url = get_database_url()
        
        # Create engine and session
        engine, SessionLocal = create_engine_and_session(db_url)
        
        # Create tables
        create_tables(engine)
        
        # Create a session for seeding data
        session = SessionLocal()
        
        try:
            # Seed pricing plans
            seed_pricing_plans(session)
            
            # Create admin user
            create_admin_user(session)
            
            print("\n✅ Database initialization completed successfully.")
            print("You should now have all tables and seed data in your database.")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n❌ Database initialization failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
