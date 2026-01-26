#!/bin/bash
# Script untuk cek Cloud Run Application Logs

echo "🔍 Checking Cloud Run Application Logs..."
echo ""

# Cek log dengan severity ERROR atau WARNING
gcloud run services logs read khasyaraka \
  --region asia-southeast2 \
  --limit 50 2>/dev/null | grep -E "(ERROR|WARNING|Traceback|Exception)" | head -30

echo ""
echo "✅ Done! Copy error messages above."
echo ""
echo "💡 Tips:"
echo "  - Jika tidak ada output, coba akses via Console:"
echo "    https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka/logs"
echo "  - Filter: Error atau Warning"
