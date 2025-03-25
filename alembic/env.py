from logging.config import fileConfig
import os
import sys
import time
import logging
from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool
from alembic import context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic.env")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import models and database configuration
from models import Base
from database import DATABASE_URL

# This is the Alembic Config object
config = context.config

# Set the SQLAlchemy URL
if DATABASE_URL:
    # Mask password for logging
    masked_url = DATABASE_URL
    if "@" in masked_url:
        parts = masked_url.split("@")
        auth_parts = parts[0].split(":")
        if len(auth_parts) > 2:
            masked_url = f"{auth_parts[0]}:****@{parts[1]}"
    
    logger.info(f"Using database URL for migrations: {masked_url}")
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
else:
    logger.warning("DATABASE_URL not set for migrations, using SQLite")
    sqlite_url = "sqlite:///./app.db"
    config.set_main_option("sqlalchemy.url", sqlite_url)

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Define retries for database connections
    MAX_RETRIES = 5
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            logger.info(f"Attempting to connect to database for migrations (attempt {retry_count + 1}/{MAX_RETRIES})")
            
            # Get the URL from config
            db_url = config.get_main_option("sqlalchemy.url")
            
            # Configure additional args based on database type
            connect_args = {}
            if db_url.startswith("postgresql"):
                connect_args = {"connect_timeout": 10}
            elif db_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
            
            # Create a custom engine with retry/reconnection settings
            connectable = create_engine(
                db_url,
                poolclass=pool.NullPool,
                connect_args=connect_args
            )
            
            # Test the connection before proceeding
            if not db_url.startswith("sqlite"):
                with connectable.connect() as test_conn:
                    test_conn.execute("SELECT 1")
                    logger.info("Database connection successful")
            else:
                logger.info("Using SQLite database, skipping connection test")
            
            # Now use the connection for migrations
            with connectable.connect() as connection:
                context.configure(
                    connection=connection, 
                    target_metadata=target_metadata
                )

                with context.begin_transaction():
                    context.run_migrations()
            
            # If we get here, migrations were successful
            logger.info("Migrations executed successfully")
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Database connection failed: {str(e)}")
            
            if retry_count < MAX_RETRIES:
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached. Could not establish database connection for migrations.")
                if db_url.startswith("sqlite"):
                    # For SQLite, we'll just proceed (it will create a new DB)
                    logger.warning("Using SQLite without verified connection")
                    connectable = create_engine(db_url, poolclass=pool.NullPool)
                    with connectable.connect() as connection:
                        context.configure(
                            connection=connection, 
                            target_metadata=target_metadata
                        )
                        with context.begin_transaction():
                            context.run_migrations()
                    break
                else:
                    raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
