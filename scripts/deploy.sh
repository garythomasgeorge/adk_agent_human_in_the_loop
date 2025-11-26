#!/bin/bash

# Exit on error
set -e

PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="hitl-poc"
REGION="us-central1"

echo "Deploying to Project: $PROJECT_ID"

# Build and Deploy
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080

echo "Deployment Complete!"
