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
config.set_main_option("sqlalchemy.url", DATABASE_URL)

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
            
            # Create a custom engine with retry/reconnection settings
            connectable = create_engine(
                DATABASE_URL,
                poolclass=pool.NullPool,
                connect_args={"connect_timeout": 10}
            )
            
            # Test the connection before proceeding
            with connectable.connect() as test_conn:
                test_conn.execute("SELECT 1")
                logger.info("Database connection successful")
            
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
                raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
