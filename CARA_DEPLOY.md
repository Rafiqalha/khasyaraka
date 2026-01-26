# 🚀 PANDUAN DEPLOY KE GOOGLE CLOUD RUN

**Langkah-langkah lengkap untuk deploy scout_os_backend ke Google Cloud Run**

---

## 📋 PRASYARAT

1. **Google Cloud Project sudah dibuat**
2. **gcloud CLI sudah terinstall dan login**
3. **Docker sudah terinstall** (untuk local testing)
4. **Environment variables sudah disiapkan:**
   - `SECRET_KEY` (JWT secret)
   - `DATABASE_URL` (Supabase connection string)
   - `REDIS_URL` (Upstash Redis URL)

---

## 🔧 LANGKAH 1: SETUP GOOGLE CLOUD

### **1.1 Login ke Google Cloud**

```bash
# Login ke Google Cloud
gcloud auth login

# Set project ID
export PROJECT_ID="your-project-id"
gcloud config set project ${PROJECT_ID}
```

### **1.2 Enable Required APIs**

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Cloud Build API
gcloud services enable cloudbuild.googleapis.com

# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com
```

### **1.3 Buat Artifact Registry Repository**

```bash
export REGION="asia-southeast2"  # Jakarta
export SERVICE_NAME="scout-os-backend"

# Buat repository untuk Docker images
gcloud artifacts repositories create scout-os-repo \
  --repository-format=docker \
  --location=${REGION} \
  --description="Scout OS Backend Docker images"
```

---

## 🔐 LANGKAH 2: SETUP SECRETS (RECOMMENDED)

### **2.1 Buat Secrets di Secret Manager**

```bash
# Buat secret untuk JWT Secret Key
echo -n "your-jwt-secret-key-here" | gcloud secrets create jwt-secret --data-file=-

# Buat secret untuk Database URL
echo -n "postgresql://user:pass@host:port/dbname" | gcloud secrets create database-url --data-file=-

# Buat secret untuk Redis URL
echo -n "rediss://default:password@host:port" | gcloud secrets create redis-url --data-file=-

# Berikan akses Cloud Run ke secrets
gcloud secrets add-iam-policy-binding jwt-secret \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding redis-url \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**ATAU gunakan environment variables langsung (lebih sederhana):**

```bash
export SECRET_KEY="your-jwt-secret-key"
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
export REDIS_URL="rediss://default:password@host:port"
```

---

## 🐳 LANGKAH 3: BUILD DOCKER IMAGE

### **3.1 Test Build Lokal (Optional)**

```bash
cd scout_os_backend

# Build image lokal
docker build -t scout-os-backend:local .

# Test run lokal
docker run -p 8080:8080 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY="${SECRET_KEY}" \
  -e DATABASE_URL="${DATABASE_URL}" \
  -e REDIS_URL="${REDIS_URL}" \
  scout-os-backend:local

# Test health endpoint
curl http://localhost:8080/health
```

### **3.2 Build dan Push ke Artifact Registry**

```bash
cd scout_os_backend

# Build dan push ke Artifact Registry
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest

# Atau gunakan Docker langsung
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest
```

---

## 🚀 LANGKAH 4: DEPLOY KE CLOUD RUN

### **4.1 Deploy dengan Secrets (Recommended)**

```bash
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
  --set-env-vars "ENVIRONMENT=production" \
  --set-secrets "SECRET_KEY=jwt-secret:latest" \
  --set-secrets "DATABASE_URL=database-url:latest" \
  --set-secrets "REDIS_URL=redis-url:latest" \
  --set-env-vars "BACKEND_CORS_ORIGINS=https://your-frontend.com"
```

### **4.2 Deploy dengan Environment Variables (Lebih Sederhana)**

```bash
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
  --set-env-vars "ENVIRONMENT=production,SECRET_KEY=${SECRET_KEY},DATABASE_URL=${DATABASE_URL},REDIS_URL=${REDIS_URL},BACKEND_CORS_ORIGINS=https://your-frontend.com"
```

---

## ✅ LANGKAH 5: VERIFIKASI DEPLOYMENT

### **5.1 Dapatkan Service URL**

```bash
# Dapatkan URL service
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
echo "Service URL: ${SERVICE_URL}"
```

### **5.2 Test Health Endpoint**

```bash
# Test health endpoint
curl ${SERVICE_URL}/health

# Expected output:
# {
#   "success": true,
#   "data": {
#     "status": "healthy",
#     "environment": "production",
#     "database": "connected",
#     "redis": "connected"
#   }
# }
```

### **5.3 Test API Endpoints**

```bash
# Test root endpoint
curl ${SERVICE_URL}/

# Test training sections
curl ${SERVICE_URL}/api/v1/training/sections
```

### **5.4 Cek Logs**

```bash
# View logs
gcloud run services logs read ${SERVICE_NAME} --region=${REGION} --limit 50

# Stream logs (real-time)
gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}
```

**Check untuk:**
- ✅ "Starting Scout OS (Khasyaraka) in production mode"
- ✅ "Training data verification passed"
- ✅ "Redis connected"
- ✅ Tidak ada error atau warning

---

## 🔄 LANGKAH 6: DATABASE MIGRATION

### **6.1 Run Migration dari Lokal**

```bash
cd scout_os_backend

# Set environment variables
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
export ENVIRONMENT=production

# Run migration
./venv/bin/python -m alembic upgrade head
```

### **6.2 Verify Migration**

```sql
-- Check migration applied
SELECT * FROM alembic_version;
-- Should show: 89f3741b3905

-- Check training data seeded
SELECT COUNT(*) FROM training_sections WHERE id = 'puk';
-- Should return: 1
```

---

## 📝 LANGKAH 7: UPDATE FRONTEND

### **7.1 Update API Base URL**

**File:** `scout_os_app/lib/core/config/environment.dart`

```dart
class Environment {
  static const String apiBaseUrl = 'https://scout-os-backend-xxxxx-xx.a.run.app';
  // Ganti dengan SERVICE_URL dari Cloud Run
}
```

---

## 🔧 TROUBLESHOOTING

### **Issue: Build Failed**

```bash
# Check build logs
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

### **Issue: Service Won't Start**

```bash
# Check logs untuk error
gcloud run services logs read ${SERVICE_NAME} --region=${REGION} --limit 100

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Redis connection failed
```

### **Issue: 502 Bad Gateway**

```bash
# Check service status
gcloud run services describe ${SERVICE_NAME} --region=${REGION}

# Check logs
gcloud run services logs read ${SERVICE_NAME} --region=${REGION}
```

### **Issue: Database Connection Failed**

**Causes:**
- `DATABASE_URL` tidak set atau salah
- Supabase firewall blocking Cloud Run IPs
- SSL configuration issue

**Fix:**
1. Verify `DATABASE_URL` di Cloud Run env vars
2. Check Supabase connection pooling settings
3. Pastikan SSL enabled di connection string

---

## 📊 QUICK REFERENCE

### **Deploy Command (Copy-Paste Ready)**

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="asia-southeast2"
export SERVICE_NAME="scout-os-backend"
export SECRET_KEY="your-jwt-secret"
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
export REDIS_URL="rediss://default:pass@host:port"

# Build and push
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest

# Deploy
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/scout-os-repo/${SERVICE_NAME}:latest \
  --platform managed --region ${REGION} --allow-unauthenticated \
  --port 8080 --memory 512Mi --cpu 1 --timeout 300 \
  --max-instances 10 --min-instances 0 --concurrency 80 \
  --set-env-vars "ENVIRONMENT=production,SECRET_KEY=${SECRET_KEY},DATABASE_URL=${DATABASE_URL},REDIS_URL=${REDIS_URL},BACKEND_CORS_ORIGINS=https://your-frontend.com"

# Get URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
echo "✅ Deployed: ${SERVICE_URL}"

# Test
curl ${SERVICE_URL}/health
```

---

## ✅ CHECKLIST DEPLOYMENT

- [ ] Google Cloud project dibuat
- [ ] APIs enabled (Cloud Run, Cloud Build, Artifact Registry)
- [ ] Artifact Registry repository dibuat
- [ ] Secrets dibuat (atau env vars disiapkan)
- [ ] Docker image built dan pushed
- [ ] Cloud Run service deployed
- [ ] Health endpoint tested (200 OK)
- [ ] Database migration run
- [ ] Logs checked (no errors)
- [ ] Frontend API URL updated

---

## 🎯 SETELAH DEPLOYMENT

1. **Test semua endpoints:**
   - `/health` → Should return healthy
   - `/api/v1/training/sections` → Should return sections
   - `/api/v1/leaderboard` → Should return leaderboard

2. **Monitor logs:**
   ```bash
   gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}
   ```

3. **Update frontend:**
   - Ganti API base URL dengan SERVICE_URL dari Cloud Run

4. **Set up monitoring:**
   - Cloud Run metrics (CPU, memory, requests)
   - Error rate monitoring
   - Health check alerts

---

**Status:** ✅ Siap untuk deployment!
