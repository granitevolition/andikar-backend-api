"""
Script to initialize database tables for the Andikar Backend API.
This creates the required tables directly using SQL statements.
"""
import os
import psycopg2
import logging
import sys
import time
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
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
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
        user_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
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

def check_connectivity(host, port, timeout=3):
    """Check if a host is reachable on the given port."""
    import socket
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

def get_connection_string():
    """Get the database connection string from environment variables.
    Prioritizes proxy connection as it's most reliable in Railway."""
    
    # Get all connection parameters
    pg_user = os.getenv("PGUSER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD", "ztJggTeesPJYVMHRWuGVbnUinMKwCWyI")
    pg_db = os.getenv("PGDATABASE", "railway")
    pg_port = os.getenv("PGPORT", "5432")
    pg_host = os.getenv("PGHOST", "postgres.railway.internal")
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "ballast.proxy.rlwy.net")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT", "11148")
    
    # Priority 1: Try DATABASE_URL if set
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        logger.info("Using DATABASE_URL from environment")
        if db_url.startswith("postgres:"):
            db_url = db_url.replace("postgres:", "postgresql:")
        return db_url

    # Priority 2: Try proxy connection (most reliable in Railway)
    if proxy_domain and proxy_port:
        logger.info(f"Using TCP proxy connection: postgresql://{pg_user}:****@{proxy_domain}:{proxy_port}/{pg_db}")
        return f"postgresql://{pg_user}:{pg_password}@{proxy_domain}:{proxy_port}/{pg_db}"
    
    # Priority 3: Try direct internal connection
    logger.info(f"Using direct connection: postgresql://{pg_user}:****@{pg_host}:{pg_port}/{pg_db}")
    return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

def create_tables():
    """Create all tables in the database."""
    connection_string = get_connection_string()
    logger.info(f"Connecting to database...")
    
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            # Connect to the database
            logger.info(f"Connection attempt {attempt+1}/{max_attempts}")
            conn = psycopg2.connect(connection_string, connect_timeout=15)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create each table
            for table_def in TABLE_DEFINITIONS:
                table_name = table_def.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                logger.info(f"Creating table: {table_name}")
                cursor.execute(table_def)
            
            logger.info("All tables created successfully")
            
            # Check if tables were created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = cursor.fetchall()
            if tables:
                logger.info(f"Tables in database: {', '.join([t[0] for t in tables])}")
            else:
                logger.warning("No tables found after creation - this may indicate a problem")
            
            # Close the connection
            cursor.close()
            conn.close()
            return True
        
        except Exception as e:
            logger.error(f"Error on attempt {attempt+1}: {str(e)}")
            if attempt < max_attempts - 1:
                backoff = min(2 ** attempt, 30)
                logger.info(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                logger.error("Maximum retry attempts reached")
                return False

if __name__ == "__main__":
    logger.info("Starting table initialization...")
    
    # Display environment variables
    logger.info("Database environment variables:")
    env_vars = [
        ("DATABASE_URL", os.getenv("DATABASE_URL", "Not set")),
        ("PGUSER", os.getenv("PGUSER", "Not set")),
        ("PGDATABASE", os.getenv("PGDATABASE", "Not set")),
        ("PGHOST", os.getenv("PGHOST", "Not set")),
        ("PGPORT", os.getenv("PGPORT", "Not set")),
        ("RAILWAY_TCP_PROXY_DOMAIN", os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "Not set")),
        ("RAILWAY_TCP_PROXY_PORT", os.getenv("RAILWAY_TCP_PROXY_PORT", "Not set"))
    ]
    
    for name, value in env_vars:
        # Mask password if present
        if name == "DATABASE_URL" and value != "Not set":
            masked_value = value.split("@")[0].split(":")
            masked_value = f"{masked_value[0]}:****@" + value.split("@")[1]
            logger.info(f"{name}: {masked_value}")
        elif name != "POSTGRES_PASSWORD":
            logger.info(f"{name}: {value}")
    
    # Check connectivity
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "ballast.proxy.rlwy.net")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT", "11148")
    if proxy_domain and proxy_port:
        logger.info(f"Checking connectivity to {proxy_domain}:{proxy_port}...")
        if check_connectivity(proxy_domain, proxy_port):
            logger.info(f"✅ Connection to proxy is available")
        else:
            logger.warning(f"⚠️ Connection to proxy is not available")
    
    # Create tables
    if create_tables():
        logger.info("✅ All tables created successfully")
    else:
        logger.error("❌ Failed to create tables")
        sys.exit(1)