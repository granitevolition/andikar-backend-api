#!/usr/bin/env python3
"""
Andikar Database Initialization Script

This script initializes the database tables and seed data for the Andikar backend.
It uses the SQLAlchemy ORM defined in models.py to create all tables.
"""

import os
import sys
import logging
import time
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("andikar-database")

# Import after logging is configured
from database import Base, engine
from models import User, PricingPlan, Conversation, Message
import bcrypt

def create_tables():
    """Create all database tables defined in the SQLAlchemy models."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error creating database tables: {e}")
        return False

def seed_pricing_plans():
    """Seed the pricing plans table with initial data."""
    from sqlalchemy.orm import Session
    
    try:
        with Session(engine) as session:
            # Check if plans already exist
            existing_plans = session.query(PricingPlan).count()
            if existing_plans > 0:
                logger.info(f"Found {existing_plans} existing pricing plans, skipping seed")
                return True
            
            # Create default pricing plans
            plans = [
                PricingPlan(
                    name="Free",
                    price=0,
                    words_limit=5000,
                    description="Basic plan with limited usage"
                ),
                PricingPlan(
                    name="Basic",
                    price=9.99,
                    words_limit=50000,
                    description="Standard plan for regular users"
                ),
                PricingPlan(
                    name="Professional",
                    price=19.99,
                    words_limit=200000,
                    description="Enhanced plan for professional users"
                ),
                PricingPlan(
                    name="Enterprise",
                    price=49.99,
                    words_limit=500000,
                    description="Advanced plan for enterprise users"
                )
            ]
            
            session.add_all(plans)
            session.commit()
            logger.info("Seeding pricing plans completed")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Error seeding pricing plans: {e}")
        return False

def create_admin_user():
    """Create the admin user if it doesn't exist."""
    from sqlalchemy.orm import Session
    
    try:
        with Session(engine) as session:
            # Check if admin user exists
            admin = session.query(User).filter(User.username == "admin").first()
            if admin:
                logger.info("Admin user already exists, skipping creation")
                return True
            
            # Get the free plan
            free_plan = session.query(PricingPlan).filter(PricingPlan.name == "Free").first()
            if not free_plan:
                logger.error("Cannot create admin user: Free plan not found")
                return False
            
            # Create password hash
            password = "admin123"  # Default admin password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Create admin user
            admin = User(
                username="admin",
                email="admin@andikar.com",
                password_hash=password_hash,
                full_name="Admin User",
                plan_id=free_plan.id,
                is_admin=True,
                is_active=True,
                payment_status="free",
                words_used=0
            )
            
            session.add(admin)
            session.commit()
            logger.info("Admin user created successfully")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Error creating admin user: {e}")
        return False

def initialize_database(max_attempts=3):
    """Initialize the database with tables and seed data."""
    attempt = 1
    while attempt <= max_attempts:
        logger.info(f"Database initialization attempt {attempt}/{max_attempts}")
        
        if create_tables() and seed_pricing_plans() and create_admin_user():
            logger.info("✅ Database initialization completed successfully!")
            return True
        
        if attempt < max_attempts:
            backoff = 2 ** attempt
            logger.info(f"Retrying in {backoff} seconds...")
            time.sleep(backoff)
        else:
            logger.error("❌ Database initialization failed after maximum attempts")
            return False
        
        attempt += 1

if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
