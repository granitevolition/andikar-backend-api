#!/usr/bin/env python3
"""
Andikar Database Diagnostic Tool

This tool helps diagnose database connection issues by checking all possible
connection methods and reporting detailed information about the database environment.
"""

import os
import sys
import socket
import logging
from urllib.parse import urlparse
import time
import traceback

try:
    import psycopg2
    import sqlalchemy
    from sqlalchemy import create_engine, text
except ImportError:
    print("Please install required packages: pip install psycopg2-binary sqlalchemy")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db-diagnostics")

def check_connectivity(host, port, timeout=3):
    """Check if a host:port is reachable."""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except socket.error as e:
        logger.warning(f"Host {host}:{port} is not reachable: {e}")
        return False

def mask_password(url):
    """Mask the password in a database URL for safe logging."""
    if not url:
        return "Not set"
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked = parsed._replace(netloc=parsed.netloc.replace(
                parsed.password, "****"))
            return masked.geturl()
        return url
    except Exception:
        return url

def test_connection(engine, conn_str, masked_conn_str):
    """Test a database connection and return detailed information."""
    try:
        conn = engine.connect()
        print(f"✅ Connection successful!")
        
        # Get database version
        try:
            result = conn.execute(text("SELECT version();"))
            row = result.fetchone()
            if row:
                print(f"Database version: {row[0]}")
        except Exception:
            print("Could not get database version")
        
        # Get current database
        try:
            result = conn.execute(text("SELECT current_database(), current_user;"))
            row = result.fetchone()
            if row:
                print(f"Current database: {row[0]}, Current user: {row[1]}")
        except Exception:
            print("Could not get current database/user information")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def get_tables(engine):
    """Get a list of tables in the database."""
    try:
        conn = engine.connect()
        
        # Try PostgreSQL version first
        try:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT LIKE 'pg_%' 
                AND schema_name != 'information_schema';
            """))
            schemas = [row[0] for row in result]
            print(f"Available schemas: {', '.join(schemas)}")
            
            for schema in schemas:
                result = conn.execute(text(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = '{schema}' 
                    AND table_type = 'BASE TABLE';
                """))
                tables = [row[0] for row in result]
                
                if tables:
                    print(f"\nTables in schema '{schema}':")
                    for table in tables:
                        print(f"  - {table}")
                else:
                    print(f"\nNo tables found in schema '{schema}'")
        except Exception:
            # Try SQLite version
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name;
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print("\nTables in database:")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("\nNo tables found in database")
        
        conn.close()
    except Exception as e:
        print(f"Could not list tables: {e}")

def test_permissions(engine):
    """Test CRUD permissions on the database."""
    try:
        conn = engine.connect()
        table_name = "andikar_permission_test"
        
        # Test CREATE TABLE permission
        print("\nTesting CREATE TABLE permission...")
        try:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, name TEXT);"))
            print("✅ CREATE TABLE: Permission granted")
        except Exception as e:
            print(f"❌ CREATE TABLE: Permission denied - {e}")
            conn.close()
            return
        
        # Test INSERT permission
        print("\nTesting INSERT permission...")
        try:
            conn.execute(text(f"INSERT INTO {table_name} (id, name) VALUES (1, 'test');"))
            print("✅ INSERT: Permission granted")
        except Exception as e:
            print(f"❌ INSERT: Permission denied - {e}")
        
        # Test UPDATE permission
        print("\nTesting UPDATE permission...")
        try:
            conn.execute(text(f"UPDATE {table_name} SET name = 'updated' WHERE id = 1;"))
            print("✅ UPDATE: Permission granted")
        except Exception as e:
            print(f"❌ UPDATE: Permission denied - {e}")
        
        # Test DELETE permission
        print("\nTesting DELETE permission...")
        try:
            conn.execute(text(f"DELETE FROM {table_name} WHERE id = 1;"))
            print("✅ DELETE: Permission granted")
        except Exception as e:
            print(f"❌ DELETE: Permission denied - {e}")
        
        # Clean up the test table
        print("\nCleaning up test table...")
        try:
            conn.execute(text(f"DROP TABLE {table_name};"))
            print("✅ DROP TABLE: Permission granted")
        except Exception as e:
            print(f"❌ DROP TABLE: Permission denied - {e}")
        
        conn.close()
    except Exception as e:
        print(f"Could not test permissions: {e}")

def main():
    print("\n🔍 Andikar Database Diagnostic Tool 🔍")
    print("This tool checks database connectivity and configuration.")
    
    print("\n==================================================")
    print(" DATABASE ENVIRONMENT VARIABLES")
    print("==================================================")
    
    # Check common environment variables
    db_url = os.getenv("DATABASE_URL")
    db_public_url = os.getenv("DATABASE_PUBLIC_URL")
    pg_user = os.getenv("PGUSER")
    pg_db = os.getenv("PGDATABASE")
    internal_domain = os.getenv("RAILWAY_PRIVATE_DOMAIN", "web.railway.internal")
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    
    print(f"DATABASE_URL: {mask_password(db_url)}")
    print(f"DATABASE_PUBLIC_URL: {mask_password(db_public_url)}")
    print(f"PGUSER: {pg_user or 'Not set'}")
    print(f"PGDATABASE: {pg_db or 'Not set'}")
    print(f"RAILWAY_PRIVATE_DOMAIN: {internal_domain or 'Not set'}")
    print(f"RAILWAY_TCP_PROXY_DOMAIN: {proxy_domain or 'Not set'}")
    print(f"RAILWAY_TCP_PROXY_PORT: {proxy_port or 'Not set'}")
    
    # Check internal connectivity
    if internal_domain:
        internal_port = os.getenv("PGPORT", "5432")
        print(f"\nChecking connectivity to {internal_domain}:{internal_port}...")
        if check_connectivity(internal_domain, int(internal_port)):
            print(f"✅ Connected to {internal_domain}:{internal_port}")
        else:
            print(f"Could not connect to {internal_domain}:{internal_port}")
    
    # Check proxy connectivity
    if proxy_domain and proxy_port:
        print(f"\nChecking connectivity to {proxy_domain}:{proxy_port}...")
        if check_connectivity(proxy_domain, int(proxy_port)):
            print(f"✅ Connected to {proxy_domain}:{proxy_port}")
        else:
            print(f"Could not connect to {proxy_domain}:{proxy_port}")
    
    # Determine the database connection string
    connection_string = None
    masked_connection_string = None
    
    # Priority 1: Use DATABASE_URL
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        connection_string = db_url
        masked_connection_string = mask_password(db_url)
        print(f"\nUsing DATABASE_URL: {masked_connection_string}")
    
    # Priority 2: Use proxy connection
    elif proxy_domain and proxy_port and pg_user:
        pg_password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
        if pg_password and pg_db:
            connection_string = f"postgresql://{pg_user}:{pg_password}@{proxy_domain}:{proxy_port}/{pg_db}"
            masked_connection_string = f"postgresql://{pg_user}:****@{proxy_domain}:{proxy_port}/{pg_db}"
            print(f"\nUsing TCP proxy connection: {masked_connection_string}")
    
    # Priority 3: Use internal connection
    elif internal_domain and pg_user:
        pg_password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
        pg_port = os.getenv("PGPORT", "5432")
        if pg_password and pg_db:
            connection_string = f"postgresql://{pg_user}:{pg_password}@{internal_domain}:{pg_port}/{pg_db}"
            masked_connection_string = f"postgresql://{pg_user}:****@{internal_domain}:{pg_port}/{pg_db}"
            print(f"\nUsing internal connection: {masked_connection_string}")
    
    if not connection_string:
        print("\nNo PostgreSQL connection configuration found, using SQLite fallback")
        connection_string = "sqlite:///andikar.db"
        masked_connection_string = connection_string
    
    print("\n==================================================")
    print(" DATABASE CONNECTION TEST")
    print("==================================================")
    
    # Create the SQLAlchemy engine
    print("Connecting to database...")
    try:
        engine = create_engine(connection_string)
        if test_connection(engine, connection_string, masked_connection_string):
            print("\n==================================================")
            print(" DATABASE TABLES")
            print("==================================================")
            get_tables(engine)
            
            print("\n==================================================")
            print(" DATABASE PERMISSIONS")
            print("==================================================")
            test_permissions(engine)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Stack trace:")
        traceback.print_exc()
    
    print("\n✨ Diagnostic Complete ✨")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error running diagnostic: {e}")
        traceback.print_exc()
