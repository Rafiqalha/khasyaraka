#!/bin/bash
# Script untuk set semua environment variables di Cloud Run

echo "🔧 Setting all environment variables di Cloud Run..."
echo ""

gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres" \
  --set-env-vars REDIS_URL="rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080

echo ""
echo "✅ Environment variables updated!"
echo ""
echo "🚀 Deploying..."
gcloud run deploy khasyaraka --source . --region asia-southeast2

echo ""
echo "✅ Done! Test endpoint:"
echo "curl https://khasyaraka-890949539640.asia-southeast2.run.app/health"
