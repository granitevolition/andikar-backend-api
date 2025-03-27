"""
Test database connection script for Andikar Backend API.
Run this script to verify the PostgreSQL connection and check existing tables.
"""
import os
import logging
import sys
import psycopg2
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-test")

def test_connection(connection_string, name="Database"):
    """Test a PostgreSQL connection string."""
    masked_conn_string = connection_string
    if '@' in masked_conn_string:
        parts = masked_conn_string.split('@')
        auth_part = parts[0].split('://')
        masked_conn_string = f"{auth_part[0]}://*****@{parts[1]}"
    
    logger.info(f"Testing connection to {name}: {masked_conn_string}")
    
    try:
        # Create connection
        conn = psycopg2.connect(connection_string, connect_timeout=10)
        
        # Test connection
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"✅ Connected to PostgreSQL: {version}")
            
            # Get database details
            cursor.execute("SELECT current_database(), current_user;")
            details = cursor.fetchone()
            logger.info(f"Database: {details[0]}")
            logger.info(f"User: {details[1]}")
            
            # Get list of schemas
            cursor.execute("SELECT schema_name FROM information_schema.schemata;")
            schemas = cursor.fetchall()
            logger.info(f"Available schemas: {', '.join([s[0] for s in schemas])}")
            
            # Get list of tables in public schema
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = cursor.fetchall()
            if tables:
                logger.info(f"Existing tables: {', '.join([t[0] for t in tables])}")
                
                # Show row counts for important tables
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                    count = cursor.fetchone()[0]
                    logger.info(f"  - {table[0]}: {count} rows")
            else:
                logger.info("No tables found in public schema")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database connection tests...")
    
    # Gather connection details
    pg_user = os.getenv("PGUSER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD", "ztJggTeesPJYVMHRWuGVbnUinMKwCWyI")
    pg_db = os.getenv("PGDATABASE", "railway")
    pg_port = os.getenv("PGPORT", "5432")
    pg_host = os.getenv("PGHOST", "postgres.railway.internal")
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "ballast.proxy.rlwy.net")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT", "11148")
    
    # Connection strings to test
    direct_conn_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    proxy_conn_string = f"postgresql://{pg_user}:{pg_password}@{proxy_domain}:{proxy_port}/{pg_db}"
    
    # Test direct connection
    if test_connection(direct_conn_string, "Direct connection"):
        logger.info("Direct connection successful")
    else:
        logger.warning("Direct connection failed, trying proxy connection...")
        
        if test_connection(proxy_conn_string, "Proxy connection"):
            logger.info("Proxy connection successful")
        else:
            logger.error("All connection attempts failed")
            sys.exit(1)
    
    logger.info("Database connection tests completed successfully")
