#!/bin/bash
# Minimal startup script for Andikar Backend API

echo "Starting Minimal Andikar Backend API..."

# Set credentials
export POSTGRES_PASSWORD=eLsHIpQoaRgtqGUMXAGzDXcIKLsIsRSf

# Try standalone connection first
echo "Testing direct PostgreSQL connection..."
python connect_db.py

# Start minimal application
echo "Starting minimal API application..."
exec python minimal_app.py
