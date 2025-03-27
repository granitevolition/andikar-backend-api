"""
Ultra-simple database connection script for Andikar Backend API.
This script attempts to connect to PostgreSQL and create tables with minimal abstractions.
"""
import os
import sys
import time
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Get database credentials from environment variables
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ztJggTeesPJYVMHRWuGVbnUinMKwCWyI")
DB_NAME = os.getenv("PGDATABASE", "railway")
DB_PORT = os.getenv("PGPORT", "5432")
DB_HOST = os.getenv("PGHOST", "postgres.railway.internal")
DB_PROXY_HOST = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "ballast.proxy.rlwy.net")
DB_PROXY_PORT = os.getenv("RAILWAY_TCP_PROXY_PORT", "11148")

# Connection strings
DIRECT_CONN_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
PROXY_CONN_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_PROXY_HOST}:{DB_PROXY_PORT}/{DB_NAME}"

def try_connect(connection_string, name="Database", print_details=True):
    """Try to connect to PostgreSQL using the given connection string."""
    try:
        print(f"Attempting to connect to {name} with: {connection_string.split('@')[0]}@...")
        
        # Create connection
        conn = psycopg2.connect(connection_string, connect_timeout=10)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Test connection
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version}")
            
            # Print database details if requested
            if print_details:
                cursor.execute("SELECT current_database(), current_user;")
                details = cursor.fetchone()
                print(f"Database: {details[0]}")
                print(f"User: {details[1]}")
                
                # Get list of schemas
                cursor.execute("SELECT schema_name FROM information_schema.schemata;")
                schemas = cursor.fetchall()
                print(f"Available schemas: {', '.join([s[0] for s in schemas])}")
                
                # Get list of tables in public schema
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public';
                """)
                tables = cursor.fetchall()
                if tables:
                    print(f"Existing tables: {', '.join([t[0] for t in tables])}")
                else:
                    print("No tables found in public schema")
        
        return conn
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return None

def create_tables(conn):
    """Create basic tables needed for the application."""
    table_definitions = [
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
        """
    ]
    
    try:
        with conn.cursor() as cursor:
            for table_def in table_definitions:
                print(f"Creating table: {table_def.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()}")
                cursor.execute(table_def)
            print("✅ All tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

def seed_data(conn):
    """Seed initial data into the database."""
    try:
        # Check if we need to seed pricing plans
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM pricing_plans")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("Seeding pricing plans...")
                
                # Create free plan
                cursor.execute("""
                    INSERT INTO pricing_plans 
                    (id, name, description, price, word_limit, requests_per_day, features) 
                    VALUES 
                    ('free', 'Free', 'Basic access to the API', 0.0, 1000, 10, '["Basic text humanization", "Limited requests"]')
                """)
                
                # Create standard plan
                cursor.execute("""
                    INSERT INTO pricing_plans 
                    (id, name, description, price, word_limit, requests_per_day, features) 
                    VALUES 
                    ('standard', 'Standard', 'Standard access with higher limits', 9.99, 10000, 100, 
                    '["Full text humanization", "AI detection", "Higher word limits"]')
                """)
                
                # Create premium plan
                cursor.execute("""
                    INSERT INTO pricing_plans 
                    (id, name, description, price, word_limit, requests_per_day, features) 
                    VALUES 
                    ('premium', 'Premium', 'Premium access with highest limits', 29.99, 100000, 1000, 
                    '["Priority processing", "Advanced humanization", "Unlimited detections", "Technical support"]')
                """)
                
                print("✅ Pricing plans seeded successfully")
            else:
                print(f"Pricing plans already exist ({count} found)")
            
            # Check if we need to create an admin user
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("Creating admin user...")
                
                import uuid
                from passlib.context import CryptContext
                
                # Generate password hash
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                admin_password = os.getenv("ADMIN_PASSWORD", "adminpassword")
                hashed_password = pwd_context.hash(admin_password)
                
                # Create admin user
                user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO users 
                    (id, username, email, full_name, hashed_password, plan_id, payment_status, is_active) 
                    VALUES 
                    (%s, 'admin', 'admin@example.com', 'Administrator', %s, 'premium', 'Paid', TRUE)
                """, (user_id, hashed_password))
                
                print("✅ Admin user created successfully")
            else:
                print("Admin user already exists")
                
        return True
    except Exception as e:
        print(f"❌ Error seeding data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to connect to PostgreSQL and initialize database."""
    print("=" * 60)
    print("ANDIKAR DATABASE CONNECTION SCRIPT")
    print("=" * 60)
    print("This script attempts to connect to PostgreSQL and create tables")
    print()
    
    # Try different connection methods in order of preference
    connections_to_try = [
        (DIRECT_CONN_STRING, "Direct connection"),
        (PROXY_CONN_STRING, "Proxy connection")
    ]
    
    connection = None
    for conn_string, name in connections_to_try:
        connection = try_connect(conn_string, name)
        if connection:
            break
        print(f"Could not connect using {name}, trying next method...")
    
    # If all attempts fail, exit
    if not connection:
        print("❌ All connection attempts failed")
        print("Please check your database configuration and network connectivity")
        sys.exit(1)
    
    # Create tables
    print("\nCreating database tables...")
    if create_tables(connection):
        # Seed initial data
        print("\nSeeding initial data...")
        if seed_data(connection):
            print("\n✅ DATABASE SETUP COMPLETE")
            print("Your PostgreSQL database is now ready to use with Andikar Backend API")
            print("=" * 60)
        else:
            print("\n⚠️ Tables created but data seeding failed")
    else:
        print("\n❌ Failed to create database tables")
        
    # Close connection
    connection.close()

if __name__ == "__main__":
    main()