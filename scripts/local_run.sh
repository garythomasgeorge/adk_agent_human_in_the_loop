#!/bin/bash

# Exit on error
set -e

echo "Building Customer App..."
cd frontend-customer
npm install
npm run build
cd ..

echo "Building Agent App..."
cd frontend-agent
npm install
npm run build
cd ..

echo "Setting up Backend Static Files..."
rm -rf backend/static
mkdir -p backend/static/customer
mkdir -p backend/static/agent

cp -r frontend-customer/dist/* backend/static/customer/
cp -r frontend-agent/dist/* backend/static/agent/

echo "Checking for existing server on port 8080..."
# Kill any existing process on port 8080
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "Found existing server on port 8080, stopping it..."
    kill -9 $(lsof -t -i:8080) || true
    sleep 1
else
    echo "No existing server found on port 8080"
fi

echo "Starting Backend..."
cd backend

# Use virtual environment if it exists
if [ -d "../.venv" ]; then
    echo "Using virtual environment..."
    ../.venv/bin/python3 -m uvicorn main:app --reload --port 8080
else
    echo "No virtual environment found, using system Python..."
    python3 -m uvicorn main:app --reload --port 8080
fi
