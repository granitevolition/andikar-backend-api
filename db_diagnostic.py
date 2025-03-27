"""
PostgreSQL diagnostic tool for Andikar Backend API.
Run this script to check database connectivity and schema.
"""
import os
import sys
import socket
import logging
import time
import traceback
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-diagnostics")

def print_section(title):
    """Print a section title with formatting."""
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)

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
    """Get the database URL from environment variables."""
    print_section("DATABASE ENVIRONMENT VARIABLES")
    
    # Display environment variables (without sensitive info)
    env_vars = {
        "DATABASE_URL": os.getenv("DATABASE_URL", "Not set"),
        "DATABASE_PUBLIC_URL": os.getenv("DATABASE_PUBLIC_URL", "Not set"),
        "PGUSER": os.getenv("PGUSER", "Not set"),
        "PGDATABASE": os.getenv("PGDATABASE", "Not set"),
        "RAILWAY_PRIVATE_DOMAIN": os.getenv("RAILWAY_PRIVATE_DOMAIN", "Not set"),
        "RAILWAY_TCP_PROXY_DOMAIN": os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "Not set"),
        "RAILWAY_TCP_PROXY_PORT": os.getenv("RAILWAY_TCP_PROXY_PORT", "Not set"),
    }
    
    # Print environment variables (hide passwords)
    for key, value in env_vars.items():
        if key == "DATABASE_URL" or key == "DATABASE_PUBLIC_URL":
            # Hide password in URLs
            if value != "Not set" and "@" in value:
                parts = value.split("@")
                auth_part = parts[0].split("://")
                masked_value = f"{auth_part[0]}://*****@{parts[1]}"
                print(f"{key}: {masked_value}")
            else:
                print(f"{key}: {value}")
        elif key == "POSTGRES_PASSWORD":
            print(f"{key}: {'*****' if value != 'Not set' else 'Not set'}")
        else:
            print(f"{key}: {value}")
    
    # Option 1: Use fully formed DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if "postgres:" in database_url:
            database_url = database_url.replace("postgres:", "postgresql:")
        print("\nUsing DATABASE_URL from environment variable")
        return database_url

    # Option 2: Try internal Railway networking
    pg_host = os.getenv("RAILWAY_PRIVATE_DOMAIN", "postgres.railway.internal")
    pg_port = 5432
    
    print(f"\nChecking connectivity to {pg_host}:{pg_port}...")
    if check_host_connectivity(pg_host, pg_port):
        pg_user = os.getenv("PGUSER", "postgres")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "")
        pg_db = os.getenv("PGDATABASE", "railway")
        
        database_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        print(f"Successfully connected to {pg_host}:{pg_port}")
        print("Using internal Railway PostgreSQL connection")
        return database_url
    else:
        print(f"Could not connect to {pg_host}:{pg_port}")

    # Option 3: Use externally accessible DATABASE_PUBLIC_URL
    database_public_url = os.getenv("DATABASE_PUBLIC_URL")
    if database_public_url:
        if "postgres:" in database_public_url:
            database_public_url = database_public_url.replace("postgres:", "postgresql:")
        print("\nUsing DATABASE_PUBLIC_URL from environment variable")
        return database_public_url

    # Option 4: Construct external URL from environment variables
    pg_public_host = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    pg_public_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    
    if pg_public_host and pg_public_port:
        pg_user = os.getenv("PGUSER", "postgres")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "")
        pg_db = os.getenv("PGDATABASE", "railway")
        
        database_url = f"postgresql://{pg_user}:{pg_pass}@{pg_public_host}:{pg_public_port}/{pg_db}"
        print("\nUsing constructed public PostgreSQL connection")
        return database_url

    # Option 5: Fallback to SQLite for local development
    print("\nNo PostgreSQL connection configuration found, using SQLite fallback")
    return "sqlite:///./andikar_diagnostic.db"

def check_database_connection(db_url):
    """Check database connection and query details."""
    print_section("DATABASE CONNECTION TEST")
    
    try:
        # Create engine
        print(f"Connecting to database...")
        
        # Handle SQLite case differently
        if db_url.startswith("sqlite"):
            engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(
                db_url,
                pool_size=1,
                pool_timeout=30,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "andikar-diagnostics"
                }
            )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                print("✅ Connection successful!")
            else:
                print("❌ Connection test failed: Unexpected result")
                return None
            
            # Get server info
            try:
                version = conn.execute(text("SELECT version()")).scalar()
                print(f"\nDatabase version: {version}")
            except:
                print("\nCould not get database version")
            
            # Get current database and user
            try:
                db_info = conn.execute(text("SELECT current_database(), current_user, current_schema")).fetchone()
                if db_info:
                    print(f"Current database: {db_info[0]}")
                    print(f"Current user: {db_info[1]}")
                    print(f"Current schema: {db_info[2]}")
            except:
                try:
                    db_info = conn.execute(text("SELECT current_database(), current_user")).fetchone()
                    if db_info:
                        print(f"Current database: {db_info[0]}")
                        print(f"Current user: {db_info[1]}")
                        print(f"Current schema: public (assumed)")
                except:
                    print("Could not get current database/user information")
            
            return engine
            
    except SQLAlchemyError as e:
        print(f"❌ Database connection error: {str(e)}")
        print("\nError traceback:")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print("\nError traceback:")
        traceback.print_exc()
        return None

def list_tables(engine):
    """List all tables in the database."""
    if not engine:
        return
    
    print_section("DATABASE TABLES")
    
    try:
        inspector = inspect(engine)
        
        # Get all schemas
        schemas = inspector.get_schema_names()
        print(f"Available schemas: {', '.join(schemas)}")
        
        # For each schema, get the tables
        for schema in schemas:
            tables = inspector.get_table_names(schema=schema)
            if tables:
                print(f"\nTables in schema '{schema}':")
                for idx, table in enumerate(tables, 1):
                    print(f"  {idx}. {table}")
                    
                    # Get column information for each table
                    try:
                        columns = inspector.get_columns(table, schema=schema)
                        if columns:
                            print(f"     Columns:")
                            for col in columns:
                                print(f"       - {col['name']} ({col['type']})")
                    except:
                        print(f"     Could not get column information")
            else:
                print(f"\nNo tables found in schema '{schema}'")
                
    except Exception as e:
        print(f"❌ Error listing tables: {str(e)}")
        traceback.print_exc()

def check_permissions(engine):
    """Check database permissions."""
    if not engine:
        return
    
    print_section("DATABASE PERMISSIONS")
    
    try:
        with engine.connect() as conn:
            # Try to create a test table
            print("Testing CREATE TABLE permission...")
            try:
                conn.execute(text("CREATE TABLE IF NOT EXISTS _andikar_test_permissions (id serial PRIMARY KEY, test_col VARCHAR(50))"))
                print("✅ CREATE TABLE: Permission granted")
            except Exception as e:
                print(f"❌ CREATE TABLE: Permission denied - {str(e)}")
            
            # Try to insert data
            print("\nTesting INSERT permission...")
            try:
                conn.execute(text("INSERT INTO _andikar_test_permissions (test_col) VALUES ('test_value')"))
                print("✅ INSERT: Permission granted")
            except Exception as e:
                print(f"❌ INSERT: Permission denied - {str(e)}")
            
            # Try to update data
            print("\nTesting UPDATE permission...")
            try:
                conn.execute(text("UPDATE _andikar_test_permissions SET test_col = 'updated_value' WHERE test_col = 'test_value'"))
                print("✅ UPDATE: Permission granted")
            except Exception as e:
                print(f"❌ UPDATE: Permission denied - {str(e)}")
            
            # Try to delete data
            print("\nTesting DELETE permission...")
            try:
                conn.execute(text("DELETE FROM _andikar_test_permissions WHERE test_col = 'updated_value'"))
                print("✅ DELETE: Permission granted")
            except Exception as e:
                print(f"❌ DELETE: Permission denied - {str(e)}")
            
            # Clean up the test table
            print("\nCleaning up test table...")
            try:
                conn.execute(text("DROP TABLE IF EXISTS _andikar_test_permissions"))
                print("✅ DROP TABLE: Permission granted")
            except Exception as e:
                print(f"❌ DROP TABLE: Permission denied - {str(e)}")
                
    except Exception as e:
        print(f"❌ Error checking permissions: {str(e)}")
        traceback.print_exc()

def run_diagnostic():
    """Run the database diagnostic tests."""
    print("\n🔍 Andikar Database Diagnostic Tool 🔍")
    print("This tool checks database connectivity and configuration.")
    
    # Step 1: Get database URL
    db_url = get_database_url()
    
    # Step 2: Check connection
    engine = check_database_connection(db_url)
    
    # Step 3: List tables
    if engine:
        list_tables(engine)
        
        # Step 4: Check permissions
        check_permissions(engine)
    
    print("\n✨ Diagnostic Complete ✨")
    
if __name__ == "__main__":
    run_diagnostic()
