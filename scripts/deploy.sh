#!/bin/bash

# Exit on error
set -e

PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="hitl-poc"
REGION="us-central1"

echo "Deploying to Project: $PROJECT_ID"

# Check if .env file exists and load GOOGLE_API_KEY
if [ -f backend/.env ]; then
    export $(grep -v '^#' backend/.env | xargs)
fi

# Verify GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GOOGLE_API_KEY not found. Please set it in backend/.env or as an environment variable."
    exit 1
fi

echo "Building and deploying..."

# Build and Deploy with environment variables
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY,GEMINI_MODEL=gemini-2.0-flash-exp

echo "Deployment Complete!"
echo "Service URL: https://$SERVICE_NAME-$(gcloud config get-value project | tr ':' '-' | tr '.' '-').run.app"
