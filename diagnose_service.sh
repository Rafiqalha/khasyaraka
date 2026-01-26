#!/bin/bash
# Diagnostic script untuk Cloud Run service

echo "🔍 Cloud Run Service Diagnostic"
echo "================================"
echo ""

echo "1️⃣ Service Status:"
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(status.conditions)" 2>&1 | head -5

echo ""
echo "2️⃣ Environment Variables:"
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(spec.template.spec.containers[0].env)" 2>&1 | grep -E "(SECRET_KEY|REDIS_URL|DATABASE_URL|ENVIRONMENT)" | head -10

echo ""
echo "3️⃣ Recent Logs (Errors/Warnings):"
gcloud run services logs read khasyaraka \
  --region asia-southeast2 \
  --limit 30 2>&1 | grep -E "(ERROR|WARNING|Exception|Traceback)" | head -15

echo ""
echo "4️⃣ Test Endpoint:"
curl -s -w "\nHTTP Status: %{http_code}\n" https://khasyaraka-890949539640.asia-southeast2.run.app/ 2>&1 | head -10

echo ""
echo "✅ Diagnostic complete!"
