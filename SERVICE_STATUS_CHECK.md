# ✅ Cloud Run Service Status Check

**Service URL:** https://khasyaraka-890949539640.asia-southeast2.run.app

---

## 🔍 Test Endpoints

### **1. Root Endpoint (Health Check)**
```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/
```

**Expected Response:**
```json
{
  "success": true,
  "message": "API is healthy",
  "data": {
    "message": "Scout OS Backend is Running",
    "architecture": "Modular Architecture",
    "environment": "production",
    "version": "1.0.0"
  }
}
```

---

### **2. Detailed Health Check**
```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Service health check completed",
  "data": {
    "status": "healthy" or "degraded",
    "environment": "production",
    "database": "connected" or "disconnected",
    "redis": "connected" or "disconnected"
  }
}
```

---

### **3. API Documentation**
```bash
# OpenAPI Docs
https://khasyaraka-890949539640.asia-southeast2.run.app/docs

# ReDoc
https://khasyaraka-890949539640.asia-southeast2.run.app/redoc
```

---

## 🧪 Quick Test Script

```bash
#!/bin/bash
# Test Cloud Run endpoints

BASE_URL="https://khasyaraka-890949539640.asia-southeast2.run.app"

echo "🔍 Testing Cloud Run Service..."
echo ""

echo "1. Root Endpoint:"
curl -s "$BASE_URL/" | jq '.' || curl -s "$BASE_URL/"
echo ""

echo "2. Health Check:"
curl -s "$BASE_URL/health" | jq '.' || curl -s "$BASE_URL/health"
echo ""

echo "3. API Docs:"
echo "   OpenAPI: $BASE_URL/docs"
echo "   ReDoc: $BASE_URL/redoc"
```

---

## 📊 Status Indicators

### **✅ Service Running (200 OK)**
- Endpoint merespons dengan status 200
- JSON response valid
- Health check menunjukkan status

### **❌ Service Not Running (503/502/404)**
- Endpoint tidak merespons
- Timeout atau connection refused
- Error 503 (Service Unavailable)

### **⚠️ Service Degraded (200 OK but degraded)**
- Endpoint merespons tapi:
  - Database disconnected
  - Redis disconnected
  - Health check menunjukkan "degraded"

---

## 🔧 Troubleshooting

### **Jika endpoint tidak merespons:**

1. **Cek Cloud Run Status:**
   ```bash
   gcloud run services describe khasyaraka \
     --region asia-southeast2 \
     --format="value(status.conditions)"
   ```

2. **Cek Logs:**
   ```bash
   gcloud run services logs read khasyaraka \
     --region asia-southeast2 \
     --limit 20
   ```

3. **Cek Environment Variables:**
   ```bash
   gcloud run services describe khasyaraka \
     --region asia-southeast2 \
     --format="value(spec.template.spec.containers[0].env)"
   ```

---

## 🚀 Next Steps

Setelah service running:

1. **Test API Endpoints:**
   - `/api/v1/auth/register` - Register user
   - `/api/v1/auth/login` - Login
   - `/api/v1/training/sections` - Get training sections
   - `/api/v1/leaderboard` - Get leaderboard

2. **Monitor Logs:**
   ```bash
   gcloud run services logs tail khasyaraka \
     --region asia-southeast2
   ```

3. **Set up Monitoring:**
   - Cloud Run metrics
   - Error rate monitoring
   - Response time tracking

---

**Service URL:** https://khasyaraka-890949539640.asia-southeast2.run.app
