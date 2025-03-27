#!/bin/bash
# Minimal startup script for Andikar Backend API

echo "Starting Minimal Andikar Backend API..."

# Set credentials based on the correct values
export POSTGRES_PASSWORD=ztJggTeesPJYVMHRWuGVbnUinMKwCWyI
export PGUSER=postgres
export PGDATABASE=railway
export PGPORT=5432
export PGHOST=postgres.railway.internal
export RAILWAY_TCP_PROXY_DOMAIN=ballast.proxy.rlwy.net
export RAILWAY_TCP_PROXY_PORT=11148

# Export database connection string
export DATABASE_URL="postgresql://postgres:ztJggTeesPJYVMHRWuGVbnUinMKwCWyI@postgres.railway.internal:5432/railway"
export DATABASE_PUBLIC_URL="postgresql://postgres:ztJggTeesPJYVMHRWuGVbnUinMKwCWyI@ballast.proxy.rlwy.net:11148/railway"

echo "Using database credentials:"
echo "- Internal URL: postgresql://$PGUSER:******@$PGHOST:$PGPORT/$PGDATABASE"
echo "- External URL: postgresql://$PGUSER:******@$RAILWAY_TCP_PROXY_DOMAIN:$RAILWAY_TCP_PROXY_PORT/$PGDATABASE"

# Try standalone connection first
echo "Testing direct PostgreSQL connection..."
python connect_db.py

# Start minimal application
echo "Starting minimal API application..."
exec python minimal_app.py
