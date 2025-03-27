"""
Script to initialize database tables for the Andikar Backend API.
This creates the required tables directly using SQL statements.
"""
import os
import psycopg2
import logging
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("init-tables")

# Table definitions (matching the SQLAlchemy models)
TABLE_DEFINITIONS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(255) PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        full_name VARCHAR(255),
        hashed_password VARCHAR(255) NOT NULL,
        plan_id VARCHAR(255) DEFAULT 'free',
        words_used INTEGER DEFAULT 0,
        payment_status VARCHAR(255) DEFAULT 'Pending',
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        api_keys JSONB DEFAULT '{}',
        is_active BOOLEAN DEFAULT TRUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
        amount FLOAT NOT NULL,
        currency VARCHAR(255) DEFAULT 'KES',
        payment_method VARCHAR(255) NOT NULL,
        status VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        transaction_metadata JSONB DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS api_logs (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
        endpoint VARCHAR(255) NOT NULL,
        request_size INTEGER NOT NULL,
        response_size INTEGER,
        processing_time FLOAT,
        status_code INTEGER,
        error VARCHAR(255),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address VARCHAR(255),
        user_agent VARCHAR(255)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rate_limits (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
        key VARCHAR(255) UNIQUE,
        requests JSONB DEFAULT '[]',
        last_updated FLOAT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pricing_plans (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        price FLOAT NOT NULL,
        currency VARCHAR(255) DEFAULT 'KES',
        billing_cycle VARCHAR(255) DEFAULT 'monthly',
        word_limit INTEGER NOT NULL,
        requests_per_day INTEGER NOT NULL,
        features JSONB DEFAULT '[]',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS webhooks (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE),
        url VARCHAR(255),
        events JSONB DEFAULT '[]',
        secret VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_triggered JSONB
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_stats (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE),
        year INTEGER,
        month INTEGER,
        day INTEGER,
        humanize_requests INTEGER DEFAULT 0,
        detect_requests INTEGER DEFAULT 0,
        words_processed INTEGER DEFAULT 0,
        total_processing_time FLOAT DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

def get_connection_string():
    """Get the database connection string from environment variables."""
    # Option 1: Direct connection string from DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    # Option 2: Construct from individual components
    pg_user = os.getenv("PGUSER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD", "ztJggTeesPJYVMHRWuGVbnUinMKwCWyI")
    pg_db = os.getenv("PGDATABASE", "railway")
    
    # Try direct connection first
    pg_host = os.getenv("PGHOST", "postgres.railway.internal")
    pg_port = os.getenv("PGPORT", "5432")
    direct_conn = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    
    # Try proxy connection if direct connection parameters are unavailable
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    if proxy_domain and proxy_port:
        proxy_conn = f"postgresql://{pg_user}:{pg_password}@{proxy_domain}:{proxy_port}/{pg_db}"
        return proxy_conn
    
    return direct_conn

def create_tables():
    """Create all tables in the database."""
    connection_string = get_connection_string()
    logger.info(f"Connecting to database...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(connection_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create each table
        for table_def in TABLE_DEFINITIONS:
            table_name = table_def.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
            logger.info(f"Creating table: {table_name}")
            cursor.execute(table_def)
        
        logger.info("All tables created successfully")
        
        # Close the connection
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting table initialization...")
    
    if create_tables():
        logger.info("✅ All tables created successfully")
    else:
        logger.error("❌ Failed to create tables")
        sys.exit(1)
