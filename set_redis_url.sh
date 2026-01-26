#!/bin/bash
# Script untuk set REDIS_URL di Cloud Run

REDIS_URL="rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379"

echo "🔧 Setting REDIS_URL di Cloud Run..."
echo ""

gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars REDIS_URL="$REDIS_URL"

echo ""
echo "✅ REDIS_URL updated!"
echo ""
echo "🚀 Deploying..."
gcloud run deploy khasyaraka --source . --region asia-southeast2

echo ""
echo "✅ Done! Cek log untuk memastikan deployment berhasil."
