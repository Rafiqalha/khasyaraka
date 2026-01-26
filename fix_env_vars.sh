#!/bin/bash
# Script untuk fix environment variables di Cloud Run

echo "🔧 Fixing Cloud Run Environment Variables..."
echo ""

# Generate SECRET_KEY
echo "Generating SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "✅ SECRET_KEY generated: ${SECRET_KEY:0:20}..."

echo ""
echo "⚠️  PENTING: Ganti YOUR_REDIS_URL dengan URL Redis yang benar!"
echo ""
read -p "Masukkan REDIS_URL (contoh: redis://host:port): " REDIS_URL

if [ -z "$REDIS_URL" ]; then
    echo "❌ REDIS_URL tidak boleh kosong!"
    exit 1
fi

echo ""
echo "Updating Cloud Run environment variables..."
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="$SECRET_KEY" \
  --set-env-vars REDIS_URL="$REDIS_URL" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080

echo ""
echo "✅ Environment variables updated!"
echo ""
echo "🚀 Deploying..."
gcloud run deploy khasyaraka --source . --region asia-southeast2

echo ""
echo "✅ Done! Cek log untuk memastikan deployment berhasil."
