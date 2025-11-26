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

echo "Starting Backend..."
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8080
