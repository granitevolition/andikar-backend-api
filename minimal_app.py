"""
Minimal FastAPI application with direct PostgreSQL connection.
No SQLAlchemy, no ORM, just raw database queries.
"""
import os
import time
import uuid
import logging
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("minimal-api")

# Hard-coded credentials from Railway
DB_USER = "postgres"
DB_PASSWORD = "eLsHIpQoaRgtqGUMXAGzDXcIKLsIsRSf"
DB_NAME = "railway"
DB_PORT = 5432
DB_HOST = "postgres.railway.internal"  # Default host

# Try alternative hosts if the default fails
ALTERNATIVE_HOSTS = [
    os.getenv("RAILWAY_PRIVATE_DOMAIN", "web.railway.internal"),
    os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
]

# App configuration
PROJECT_NAME = "Andikar Backend API (Minimal)"
PROJECT_VERSION = "1.0.0"

# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    description="Minimal Backend API Gateway for Andikar AI services",
    version=PROJECT_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global database connection pool
db_pool = None

def get_db_connection():
    """Get a database connection from the pool."""
    global db_pool
    
    # If pool not initialized, create it
    if db_pool is None:
        try:
            # Try primary host
            logger.info(f"Connecting to database at {DB_HOST}:{DB_PORT}...")
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                connect_timeout=10
            )
            conn.autocommit = True
            logger.info("Connected to primary database host")
            return conn
        except Exception as e:
            logger.error(f"Error connecting to primary database host: {e}")
            
            # Try alternative hosts
            for host in ALTERNATIVE_HOSTS:
                if not host:
                    continue
                    
                try:
                    logger.info(f"Trying alternative host {host}...")
                    conn = psycopg2.connect(
                        dbname=DB_NAME,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        host=host,
                        port=DB_PORT,
                        connect_timeout=10
                    )
                    conn.autocommit = True
                    logger.info(f"Connected to alternative host {host}")
                    return conn
                except Exception as e:
                    logger.error(f"Error connecting to {host}: {e}")
            
            # If all attempts failed, raise exception
            raise Exception("All database connection attempts failed")
    
    # Return existing connection
    return db_pool

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection on startup."""
    global db_pool
    
    try:
        # Initialize database connection
        db_pool = get_db_connection()
        
        # Test connection
        with db_pool.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
            
            # Initialize database tables
            init_database()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        import traceback
        logger.error(traceback.format_exc())

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection on shutdown."""
    global db_pool
    if db_pool:
        db_pool.close()
        logger.info("Database connection closed")

def init_database():
    """Initialize database tables."""
    global db_pool
    
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
        with db_pool.cursor() as cursor:
            for table_def in table_definitions:
                cursor.execute(table_def)
            logger.info("All tables created successfully")
            
            # Check if we need to seed pricing plans
            cursor.execute("SELECT COUNT(*) FROM pricing_plans")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("Seeding pricing plans...")
                
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
                
                logger.info("Pricing plans seeded successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

class User(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint serving a simple HTML page."""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{PROJECT_NAME}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
                color: #333;
                line-height: 1.6;
            }}
            header {{
                margin-bottom: 2rem;
                border-bottom: 1px solid #eee;
                padding-bottom: 1rem;
            }}
            .card {{
                background: #f9fafb;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                border: 1px solid #e5e7eb;
            }}
            footer {{
                margin-top: 3rem;
                padding-top: 1rem;
                border-top: 1px solid #eee;
                text-align: center;
                font-size: 0.875rem;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>{PROJECT_NAME}</h1>
            <p>Version {PROJECT_VERSION} - Minimal implementation with direct PostgreSQL connection</p>
        </header>
        
        <div class="card">
            <h2>API Endpoints</h2>
            <ul>
                <li><a href="/health">/health</a> - Check system health</li>
                <li><a href="/status">/status</a> - Check database status</li>
                <li><a href="/users">/users</a> - List all users</li>
                <li><a href="/tables">/tables</a> - List all database tables</li>
                <li><a href="/register">/register</a> - Register a new user (POST)</li>
            </ul>
        </div>
        
        <div class="card">
            <h2>Database Connection</h2>
            <p>This application connects directly to PostgreSQL using psycopg2, without any ORM.</p>
            <p>It tries multiple hosts if the primary connection fails.</p>
        </div>
        
        <footer>
            &copy; {datetime.now().year} Andikar Backend API
        </footer>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "unhealthy"
    db_details = {}
    
    try:
        # Test database connection
        with db_pool.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                db_status = "healthy"
                
                # Get database details
                try:
                    cursor.execute("SELECT version()")
                    db_details["version"] = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT current_database(), current_user")
                    result = cursor.fetchone()
                    db_details["database"] = result[0]
                    db_details["user"] = result[1]
                except Exception as e:
                    db_details["error"] = str(e)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": db_status,
            "api": "healthy"
        },
        "database_details": db_details
    }

@app.get("/status")
async def db_status():
    """Database status endpoint with detailed information."""
    try:
        with db_pool.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get database version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()["version"]
            
            # Get connection information
            cursor.execute("""
                SELECT current_database(), current_user, inet_server_addr(), inet_server_port()
            """)
            conn_info = cursor.fetchone()
            
            # Count tables
            cursor.execute("""
                SELECT table_schema, COUNT(*) as table_count
                FROM information_schema.tables
                GROUP BY table_schema
                ORDER BY table_schema
            """)
            schemas = cursor.fetchall()
            
            # Get table details from public schema
            cursor.execute("""
                SELECT 
                    table_name, 
                    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) AS column_count
                FROM 
                    information_schema.tables t
                WHERE 
                    table_schema = 'public'
                ORDER BY 
                    table_name
            """)
            tables = cursor.fetchall()
            
            # Check if tables have records
            table_records = []
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table['table_name']}")
                    count = cursor.fetchone()["count"]
                    table_records.append({
                        "table": table["table_name"],
                        "record_count": count
                    })
                except Exception as e:
                    logger.error(f"Error counting records in {table['table_name']}: {e}")
            
            return {
                "status": "connected",
                "version": version,
                "connection": conn_info,
                "schemas": schemas,
                "tables": tables,
                "records": table_records
            }
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/users")
async def list_users():
    """List all users in the database."""
    try:
        with db_pool.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, username, email, full_name, plan_id, words_used, payment_status, 
                       joined_date, is_active
                FROM users
                ORDER BY joined_date DESC
            """)
            users = cursor.fetchall()
            
            return {"users": users, "count": len(users)}
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return {"error": str(e)}

@app.get("/tables")
async def list_tables():
    """List all tables in the database with their structure."""
    try:
        with db_pool.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get all tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            result = []
            
            # Get columns for each table
            for table in tables:
                table_name = table["table_name"]
                
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()
                
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()["count"]
                
                result.append({
                    "table_name": table_name,
                    "columns": columns,
                    "record_count": count
                })
            
            return result
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return {"error": str(e)}

@app.post("/register")
async def register_user(user: User):
    """Register a new user."""
    try:
        # Generate password hash
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(user.password)
        
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        with db_pool.cursor() as cursor:
            # Check if username already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (user.username,))
            if cursor.fetchone()[0] > 0:
                raise HTTPException(status_code=400, detail="Username already exists")
            
            # Check if email already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (user.email,))
            if cursor.fetchone()[0] > 0:
                raise HTTPException(status_code=400, detail="Email already exists")
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users 
                (id, username, email, full_name, hashed_password, plan_id, payment_status, words_used, joined_date, is_active) 
                VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                user.username,
                user.email,
                user.full_name,
                hashed_password,
                "free",  # Default plan
                "Paid",  # Free plan is always paid
                0,       # Initial words count
                datetime.now(),
                True     # Active by default
            ))
            
            return {
                "id": user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "plan_id": "free",
                "message": "User registered successfully"
            }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")

@app.post("/reset-database")
async def reset_database():
    """Reset the database (for testing only)."""
    try:
        with db_pool.cursor() as cursor:
            # Drop all tables
            cursor.execute("""
                DO $$ 
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
            
            # Reinitialize database
            init_database()
            
            return {"message": "Database reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting {PROJECT_NAME} on port {port}")
    uvicorn.run("minimal_app:app", host="0.0.0.0", port=port, reload=False)
