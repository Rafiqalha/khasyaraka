# 🔧 Cloud Run Startup Timeout Fix

**Issue:** Container failed to start and listen on port 8080 within Cloud Run timeout

**Root Cause:**
- Startup event (`@app.on_event("startup")`) was blocking on database connection
- If database connection failed or timed out, app never started listening
- Cloud Run requires app to listen on PORT within startup timeout (default: 60s)

---

## ✅ Fix Applied

### **1. Non-Blocking Startup Event**

**Before:**
```python
@app.on_event("startup")
async def startup_event():
    # Blocking database connection
    async with SessionLocal() as db:
        verification_result = await verify_training_data(db)
        # If this fails/times out, app never starts listening
```

**After:**
```python
@app.on_event("startup")
async def startup_event():
    # Non-blocking background task
    async def verify_training_data_background():
        try:
            async with asyncio.timeout(10.0):  # 10s max timeout
                # Database check...
        except asyncio.TimeoutError:
            logger.warning("Verification timeout - App continues")
    
    # Run in background - app starts listening immediately
    asyncio.create_task(verify_training_data_background())
    logger.info("✅ Application startup complete - Server ready")
```

### **2. Key Improvements**

- ✅ **Non-blocking:** Database verification runs in background task
- ✅ **Timeout protection:** 10 second max timeout for DB check
- ✅ **Graceful degradation:** App starts even if DB check fails
- ✅ **Immediate listening:** Server starts accepting requests immediately

---

## 🧪 Verification

**Test locally:**
```bash
# Start app (should start immediately)
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Expected output:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     ✅ Application startup complete - Server ready to accept requests
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Test with slow database:**
```bash
# Even if database is slow/unavailable, app should start
# Database verification will log warning but app continues
```

---

## 🚀 Cloud Run Deployment

**Deploy:**
```bash
gcloud run deploy khasyaraka \
  --source . \
  --platform managed \
  --region asia-southeast2 \
  --allow-unauthenticated \
  --timeout 300 \
  --cpu 1 \
  --memory 512Mi
```

**Expected behavior:**
- ✅ Container starts within Cloud Run timeout
- ✅ App listens on port 8080 immediately
- ✅ Database verification runs in background
- ✅ Health endpoint responds: `GET /health`

---

## 📝 Additional Notes

### **Startup Sequence:**

1. **FastAPI app initialization** (instant)
2. **Startup event triggered** (non-blocking)
3. **Background task created** for DB verification
4. **App starts listening** on port 8080 ✅
5. **DB verification completes** (or times out) in background

### **Health Check Endpoints:**

- `GET /` - Simple health check (no DB required)
- `GET /health` - Detailed health check (with DB/Redis status)

Both endpoints are available immediately after startup.

---

## 🔍 Troubleshooting

**If container still fails to start:**

1. **Check logs:**
   ```bash
   gcloud run services logs read khasyaraka --limit 50
   ```

2. **Check environment variables:**
   - `DATABASE_URL` must be set
   - `REDIS_URL` must be set (or will use localhost fallback)
   - `SECRET_KEY` must be set
   - `ENVIRONMENT=production`

3. **Check import errors:**
   ```bash
   docker run --rm scout-os-backend python -c "import app.main"
   ```

4. **Test Docker image locally:**
   ```bash
   docker build -t scout-os-backend .
   docker run -p 8080:8080 \
     -e DATABASE_URL="your-db-url" \
     -e REDIS_URL="your-redis-url" \
     -e SECRET_KEY="your-secret" \
     -e ENVIRONMENT="production" \
     scout-os-backend
   ```

---

**Status:** ✅ Fixed - Startup is now non-blocking and Cloud Run compatible
