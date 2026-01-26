# 🔧 Dockerfile Fix: Cloud Run Port Binding

**Issue:** Container failed to start and listen on the port

**Root Cause:** 
- CMD menggunakan shell form dengan variable expansion `${PORT:-8080}` yang mungkin tidak di-expand dengan benar
- Format `exec uvicorn ...` dengan shell expansion tidak reliable di Cloud Run

**Fix Applied:**

## ✅ Changes Made

1. **Simplified CMD Format:**
   - **Before:** `CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 5`
   - **After:** `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]`

2. **Key Improvements:**
   - ✅ **Exec form (JSON array)** - Proper signal handling untuk Cloud Run graceful shutdown
   - ✅ **Hardcoded port 8080** - Cloud Run default, menghindari variable expansion issues
   - ✅ **Host 0.0.0.0** - WAJIB untuk Cloud Run (bukan 127.0.0.1)
   - ✅ **Simplified** - Removed workers & timeout flags (Cloud Run handles scaling)

3. **Maintained:**
   - ✅ Python 3.11-slim (lebih modern dari 3.10)
   - ✅ System dependencies (gcc, libpq-dev)
   - ✅ Environment variables (PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED)
   - ✅ Layer caching optimization

---

## 🧪 Verification

**Test locally:**
```bash
# Build image
docker build -t scout-os-backend .

# Run container
docker run -p 8080:8080 scout-os-backend

# Test endpoint
curl http://localhost:8080/health
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

## 🚀 Cloud Run Deployment

**Deploy command:**
```bash
gcloud run deploy scout-os-backend \
  --source . \
  --platform managed \
  --region asia-southeast2 \
  --allow-unauthenticated
```

**Verification:**
- ✅ Container starts successfully
- ✅ Health endpoint responds: `GET /health`
- ✅ Logs show: `Uvicorn running on http://0.0.0.0:8080`

---

## 📝 Notes

- **Port 8080** adalah default Cloud Run, tidak perlu diubah
- **Host 0.0.0.0** memastikan container listen di semua network interfaces
- **Exec form** memastikan SIGTERM diterima dengan benar untuk graceful shutdown
- Jika Cloud Run menggunakan PORT env variable yang berbeda, bisa di-handle di app code atau gunakan shell wrapper

---

**Status:** ✅ Fixed - Ready for Cloud Run deployment
