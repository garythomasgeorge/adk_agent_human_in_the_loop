# Stage 1: Build Customer App
FROM node:18-alpine as build-customer
WORKDIR /app
COPY frontend-customer/package*.json ./
RUN npm install
COPY frontend-customer/ .
RUN npm run build

# Stage 2: Build Agent App
FROM node:18-alpine as build-agent
WORKDIR /app
COPY frontend-agent/package*.json ./
RUN npm install
COPY frontend-agent/ .
RUN npm run build

# Stage 3: Python Runtime
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontends to static directory
# Structure: /app/static/customer and /app/static/agent
COPY --from=build-customer /app/dist /app/static/customer
COPY --from=build-agent /app/dist /app/static/agent

# Expose port
EXPOSE 8080

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
