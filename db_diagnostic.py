"""
Database diagnostic tool for Andikar Backend API.
This script performs comprehensive connectivity tests for PostgreSQL.
"""
import os
import psycopg2
import logging
import sys
import socket
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-diagnostics")

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f" {text}")
    print("=" * 50)

def check_host_connectivity(host, port, timeout=3):
    """Check if a host is reachable on the given port."""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.close()
        return True
    except Exception as e:
        logger.warning(f"Host {host}:{port} is not reachable: {str(e)}")
        return False

def get_connection_options():
    """Get all possible connection options from environment variables."""
    options = {}
    
    # Direct connection parameters
    options['pg_user'] = os.getenv("PGUSER", "postgres")
    options['pg_password'] = os.getenv("POSTGRES_PASSWORD", "ztJggTeesPJYVMHRWuGVbnUinMKwCWyI")
    options['pg_db'] = os.getenv("PGDATABASE", "railway")
    options['pg_port'] = os.getenv("PGPORT", "5432")
    options['pg_host'] = os.getenv("PGHOST", "postgres.railway.internal")
    
    # Proxy connection parameters
    options['proxy_domain'] = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "ballast.proxy.rlwy.net")
    options['proxy_port'] = os.getenv("RAILWAY_TCP_PROXY_PORT", "11148")
    
    # Full connection strings
    options['database_url'] = os.getenv("DATABASE_URL")
    
    return options

def test_connection(connection_string, name, password_hint=""):
    """Test a database connection and return details."""
    try:
        print(f"Testing connection to {name}...")
        
        conn = psycopg2.connect(connection_string, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print(f"✅ Connection successful!")
        
        # Get database version
        try:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"PostgreSQL version: {version}")
        except Exception as e:
            print(f"Could not get database version: {e}")
        
        # Get database/user info
        try:
            cursor.execute("SELECT current_database(), current_user")
            db, user = cursor.fetchone()
            print(f"Database: {db}, User: {user}")
        except Exception as e:
            print(f"Could not get current database/user information: {e}")
        
        # Get schemas
        try:
            cursor.execute("SELECT schema_name FROM information_schema.schemata")
            schemas = [row[0] for row in cursor.fetchall()]
            print(f"Available schemas: {', '.join(schemas)}")
        except Exception as e:
            print(f"Could not get schema information: {e}")
        
        # Get tables
        try:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = cursor.fetchall()
            if tables:
                table_names = [t[0] for t in tables]
                print(f"Tables in 'public' schema: {', '.join(table_names)}")
                
                # Count rows in each table
                for table in table_names:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"  - {table}: {count} rows")
                    except Exception as e:
                        print(f"  - {table}: Error counting rows - {str(e)}")
            else:
                print("No tables found in 'public' schema")
        except Exception as e:
            print(f"Could not get table information: {e}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_database_permissions(connection_string):
    """Test database permissions by creating and modifying a test table."""
    print_header("DATABASE PERMISSIONS")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(connection_string, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Test CREATE TABLE permission
        print("Testing CREATE TABLE permission...")
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS _diagnostic_test (id SERIAL PRIMARY KEY, test_text VARCHAR(255))")
            print("✅ CREATE TABLE: Permission granted")
        except Exception as e:
            print(f"❌ CREATE TABLE: Permission denied - {str(e)}")
            conn.close()
            return False
        
        # Test INSERT permission
        print("\nTesting INSERT permission...")
        try:
            cursor.execute("INSERT INTO _diagnostic_test (test_text) VALUES ('test data')")
            print("✅ INSERT: Permission granted")
        except Exception as e:
            print(f"❌ INSERT: Permission denied - {str(e)}")
            conn.close()
            return False
        
        # Test UPDATE permission
        print("\nTesting UPDATE permission...")
        try:
            cursor.execute("UPDATE _diagnostic_test SET test_text = 'updated test data' WHERE test_text = 'test data'")
            print("✅ UPDATE: Permission granted")
        except Exception as e:
            print(f"❌ UPDATE: Permission denied - {str(e)}")
            conn.close()
            return False
        
        # Test DELETE permission
        print("\nTesting DELETE permission...")
        try:
            cursor.execute("DELETE FROM _diagnostic_test WHERE test_text = 'updated test data'")
            print("✅ DELETE: Permission granted")
        except Exception as e:
            print(f"❌ DELETE: Permission denied - {str(e)}")
            conn.close()
            return False
        
        # Clean up
        print("\nCleaning up test table...")
        try:
            cursor.execute("DROP TABLE _diagnostic_test")
            print("✅ DROP TABLE: Permission granted")
        except Exception as e:
            print(f"❌ DROP TABLE: Permission denied - {str(e)}")
            conn.close()
            return False
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Permission test failed: {str(e)}")
        return False

def main():
    """Run comprehensive database diagnostics."""
    print("🔍 Andikar Database Diagnostic Tool 🔍")
    print("This tool checks database connectivity and configuration.")
    
    # Get all connection options
    options = get_connection_options()
    
    # Print environment variables
    print_header("DATABASE ENVIRONMENT VARIABLES")
    env_vars = [
        ("DATABASE_URL", options.get('database_url', "Not set")),
        ("PGUSER", options.get('pg_user', "Not set")),
        ("PGDATABASE", options.get('pg_db', "Not set")),
        ("PGHOST", options.get('pg_host', "Not set")),
        ("PGPORT", options.get('pg_port', "Not set")),
        ("RAILWAY_TCP_PROXY_DOMAIN", options.get('proxy_domain', "Not set")),
        ("RAILWAY_TCP_PROXY_PORT", options.get('proxy_port', "Not set"))
    ]
    
    for name, value in env_vars:
        if name == "DATABASE_URL" and value != "Not set":
            # Safely mask the password
            try:
                parts = value.split(":")
                masked = f"{parts[0]}:{parts[1]}:****@" + value.split("@")[1]
                print(f"{name}: {masked}")
            except (AttributeError, IndexError):
                print(f"{name}: <error masking URL>")
        elif name != "POSTGRES_PASSWORD":
            print(f"{name}: {value}")
    
    # Test connectivity to hosts
    proxy_host = options.get('proxy_domain')
    proxy_port = options.get('proxy_port')
    if proxy_host and proxy_port:
        print(f"\nChecking connectivity to {proxy_host}:{proxy_port}...")
        if check_host_connectivity(proxy_host, proxy_port):
            print(f"✅ Connection to {proxy_host}:{proxy_port} is available")
        else:
            print(f"❌ Could not connect to {proxy_host}:{proxy_port}")
    
    # Test database connections
    print_header("DATABASE CONNECTION TEST")
    
    # Build connection strings
    connection_strings = []
    
    # Priority 1: External proxy connection (most reliable)
    if proxy_host and proxy_port:
        proxy_conn_string = f"postgresql://{options.get('pg_user')}:{options.get('pg_password')}@{proxy_host}:{proxy_port}/{options.get('pg_db')}"
        connection_strings.append((proxy_conn_string, "Railway TCP Proxy"))
    
    # Priority 2: Direct database URL if set
    if options.get('database_url'):
        db_url = options.get('database_url')
        if db_url.startswith("postgres:"):
            db_url = db_url.replace("postgres:", "postgresql:")
        connection_strings.append((db_url, "DATABASE_URL"))
    
    # Test each connection
    success = False
    working_connection = None
    
    for conn_string, name in connection_strings:
        if test_connection(conn_string, name):
            success = True
            working_connection = conn_string
            break
        print(f"Trying next connection method...")
    
    if not success:
        print("❌ All connection attempts failed")
        return
    
    # Test database permissions
    if working_connection:
        test_database_permissions(working_connection)
    
    print("\n✨ Diagnostic Complete ✨")

if __name__ == "__main__":
    main()