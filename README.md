# Andikar Backend API

A robust backend API gateway for the Andikar AI ecosystem with PostgreSQL database integration on Railway.

## Features

- Complete REST API with authentication
- Integration with external AI services
- PostgreSQL database for data persistence
- Admin dashboard with analytics
- Payment processing integration

## Database Setup

This application is configured to automatically connect to a PostgreSQL database on Railway. It follows a robust connection strategy:

1. First tries `postgres.railway.internal` private network connection
2. If that fails, uses the public TCP proxy connection via `RAILWAY_TCP_PROXY_DOMAIN`
3. As a last resort, falls back to SQLite for development/testing

### Environment Variables for Database Connection

The following environment variables are used for database connection:

- `DATABASE_URL` - Full PostgreSQL connection string (preferred)
- `PGUSER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `PGDATABASE` - PostgreSQL database name
- `PGHOST` - PostgreSQL host (typically postgres.railway.internal)
- `PGPORT` - PostgreSQL port (typically 5432)
- `RAILWAY_TCP_PROXY_DOMAIN` - External Railway proxy domain
- `RAILWAY_TCP_PROXY_PORT` - External Railway proxy port

All of these environment variables are automatically set by Railway when you add a PostgreSQL service to your project.

### Testing Database Connection

To test the database connection, you can run:

```bash
python test_db_connection.py
```

This script will attempt to connect to the database using both direct and proxy methods, and will display information about the database if successful.

### Initializing the Database

To initialize the database with tables and seed data, run:

```bash
python initialize_database.py
```

This script will:
1. Connect to the database using the configured connection details
2. Create all necessary tables if they don't exist
3. Seed initial data like pricing plans and admin user

## Database Models

The application uses SQLAlchemy ORM with the following models:

- **User** - User accounts with authentication
- **Transaction** - Payment transactions
- **APILog** - API usage logs
- **RateLimit** - Rate limiting data
- **PricingPlan** - Subscription tiers
- **Webhook** - External service webhooks
- **UsageStat** - Usage statistics

Tables are automatically created on startup if they don't exist.

## Deployment

### On Railway

1. Link your GitHub repository to Railway
2. Add a PostgreSQL service to your project
3. Railway will automatically detect the Dockerfile and build/deploy

### Manually

1. Install Docker
2. Build the Docker image: `docker build -t andikar-backend-api .`
3. Run with PostgreSQL: `docker run -p 8080:8080 -e DATABASE_URL=postgresql://user:pass@host:port/db andikar-backend-api`

## Development

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)

### Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables or create a .env file
4. Run the application: `python app.py`

## API Endpoints

The API provides various endpoints:

- `/` - Root endpoint with API documentation
- `/token` - Authentication endpoint
- `/users/*` - User management
- `/api/humanize` - Text humanization
- `/api/detect` - AI content detection
- `/api/payments/*` - Payment processing
- `/dashboard` - Admin metrics
- `/health` - System health check
- `/status` - Status for health checks

## Troubleshooting Database Connection

If you're experiencing database connection issues:

1. **Check logs:** Look for connection errors in the application logs
2. **Verify environment variables:** Make sure all required variables are set
3. **Run test script:** Use `python test_db_connection.py` to diagnose connection issues
4. **Initialize database:** Use `python initialize_database.py` to set up tables
5. **Check network connectivity:** Ensure the application can reach the database
6. **Check database status:** Verify the PostgreSQL service is running
7. **Database reset:** Use `/admin/database/reset?confirm=yes` (admin only)

For manual database initialization, you can also use the `/admin/database/seed` endpoint.