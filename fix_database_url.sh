#!/bin/bash
# Script untuk fix DATABASE_URL format di Cloud Run

echo "🔧 Fixing DATABASE_URL format di Cloud Run..."
echo ""

# Update DATABASE_URL dengan format postgresql+asyncpg://
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --update-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

echo ""
echo "✅ DATABASE_URL updated!"
echo ""
echo "🚀 Deploying..."
gcloud run deploy khasyaraka --source . --region asia-southeast2

echo ""
echo "✅ Done! Test endpoint:"
echo "curl https://khasyaraka-890949539640.asia-southeast2.run.app/health"
