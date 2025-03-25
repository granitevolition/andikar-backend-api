#!/usr/bin/env python
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

print("Initializing database...")

# Check if DATABASE_URL or DATABASE_PUBLIC_URL environment variable is set
if os.environ.get("DATABASE_PUBLIC_URL"):
    print("Using DATABASE_PUBLIC_URL.")
    os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]
elif not os.environ.get("DATABASE_URL"):
    print("Warning: No DATABASE_URL or DATABASE_PUBLIC_URL provided. Using default SQLite database.")
    os.environ["DATABASE_URL"] = "sqlite:///./andikar.db"

db_url = os.environ.get("DATABASE_URL")

# Check database connection
print("Checking database connection...")
max_retries = 5
retry_interval = 3

for i in range(max_retries):
    try:
        engine = create_engine(db_url)
        conn = engine.connect()
        print("Database connection successful")
        conn.close()
        break
    except OperationalError as e:
        if i < max_retries - 1:
            print(f"Database connection failed, retrying in {retry_interval} seconds... ({i+1}/{max_retries})")
            print(f"Error: {str(e)}")
            time.sleep(retry_interval)
        else:
            print("Failed to connect to the database after multiple retries")
            raise

# Initialize database tables
print("Checking if database tables already exist...")
try:
    engine = create_engine(db_url)
    conn = engine.connect()
    try:
        # Check if 'users' table exists
        result = conn.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name='users'")).fetchone()
        if result:
            print("Database tables already exist, skipping migrations")
        else:
            print("Creating database tables...")
            from models import Base
            Base.metadata.create_all(engine)
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error checking database: {str(e)}")
        print("Creating database tables as fallback...")
        from models import Base
        Base.metadata.create_all(engine)
        print("Database tables created successfully")
    conn.close()
except Exception as e:
    print(f"Error initializing database: {str(e)}")
    raise

print("Database initialization complete!")

# Add default data
try:
    from database import get_db
    from models import User, PricingPlan
    from auth import get_password_hash
    
    db = next(get_db())
    
    # Check if any pricing plans exist
    if db.query(PricingPlan).count() == 0:
        print("Adding default pricing plans...")
        default_plans = [
            PricingPlan(
                id="free",
                name="Free Plan",
                description="Basic features for trying out the service",
                price=0,
                word_limit=1000,
                requests_per_day=10,
                features=["Humanize text (limited)", "AI detection (limited)"]
            ),
            PricingPlan(
                id="basic",
                name="Basic Plan",
                description="Standard features for regular users",
                price=999.00,
                word_limit=10000,
                requests_per_day=50,
                features=["Humanize text", "AI detection", "Email support"]
            ),
            PricingPlan(
                id="premium",
                name="Premium Plan",
                description="Advanced features for professional users",
                price=2999.00,
                word_limit=50000,
                requests_per_day=100,
                features=["Humanize text", "AI detection", "Priority support", "API access"]
            )
        ]
        db.add_all(default_plans)
        db.commit()
        print("Default pricing plans added successfully")
    
    # Check if admin user exists
    if not db.query(User).filter(User.username == "admin").first():
        print("Creating admin user...")
        admin_user = User(
            username="admin",
            email="admin@andikar.com",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),  # Change this in production!
            plan_id="premium",
            payment_status="Paid",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("Admin user created successfully")
        
    print("Database initialization and default data complete!")
except Exception as e:
    print(f"Error adding default data: {str(e)}")
    # Continue anyway as this is not critical
