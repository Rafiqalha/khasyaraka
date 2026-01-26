#!/bin/bash
# 🚀 Quick Deployment Script for Google Cloud Run
# Usage: ./deploy.sh

set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
SERVICE_NAME="scout-os-backend"
REGION="${GCP_REGION:-asia-southeast2}"

# Environment Variables (set these before running)
SECRET_KEY="${SECRET_KEY:-}"
DATABASE_URL="${DATABASE_URL:-}"
REDIS_URL="${REDIS_URL:-}"
BACKEND_CORS_ORIGINS="${BACKEND_CORS_ORIGINS:-*}"

echo "🚀 Deploying Scout OS Backend to Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo ""

# Validate required variables
if [ -z "$SECRET_KEY" ] || [ -z "$DATABASE_URL" ] || [ -z "$REDIS_URL" ]; then
    echo "❌ ERROR: Missing required environment variables!"
    echo ""
    echo "Please set:"
    echo "  export SECRET_KEY='your-jwt-secret'"
    echo "  export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    echo "  export REDIS_URL='rediss://default:pass@host:port'"
    echo ""
    exit 1
fi

# Step 1: Build and push
echo "📦 Building Docker image..."
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest

# Step 2: Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --concurrency 80 \
  --set-env-vars "ENVIRONMENT=production,SECRET_KEY=${SECRET_KEY},DATABASE_URL=${DATABASE_URL},REDIS_URL=${REDIS_URL},BACKEND_CORS_ORIGINS=${BACKEND_CORS_ORIGINS}"

# Step 3: Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
echo ""
echo "✅ Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""

# Step 4: Test health endpoint
echo "🧪 Testing health endpoint..."
sleep 5  # Wait for service to be ready
curl -s ${SERVICE_URL}/health | jq . || curl -s ${SERVICE_URL}/health

echo ""
echo "📝 Next steps:"
echo "1. Run database migrations: alembic upgrade head"
echo "2. Update frontend API URL: ${SERVICE_URL}"
echo "3. Test endpoints: curl ${SERVICE_URL}/api/v1/training/sections"
echo ""
echo "📊 View logs:"
echo "  gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}"
