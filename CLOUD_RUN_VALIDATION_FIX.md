# 🔧 Cloud Run Pydantic ValidationError Fix

**Issue:** `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings`

**Root Cause:**
- `SECRET_KEY` was defined as `Field(...)` (required field)
- Pydantic raises ValidationError during `Settings()` initialization if field is missing
- In Cloud Run, if `SECRET_KEY` env var is not set, app crashes before startup
- Error occurs **before** `model_post_init()` validation runs

---

## ✅ Fix Applied

### **1. Made SECRET_KEY Optional at Init**

**Before:**
```python
SECRET_KEY: str = Field(..., description="JWT secret key (REQUIRED for authentication)")
# ❌ Pydantic fails immediately if SECRET_KEY env var is missing
```

**After:**
```python
SECRET_KEY: str = Field(default="", description="JWT secret key (REQUIRED in production)")
# ✅ Settings() can initialize, validation happens in model_post_init()
```

### **2. Validation Still Enforced**

The `model_post_init()` method already validates `SECRET_KEY` in production:

```python
def model_post_init(self, __context) -> None:
    is_true_production = (
        self.ENVIRONMENT == "production" and
        not os.path.exists(".env")
    )
    
    if is_true_production:
        # Check SECRET_KEY
        if not self.SECRET_KEY or self.SECRET_KEY == "":
            raise ValueError(
                "Missing required environment variable in production: SECRET_KEY. "
                "Please set SECRET_KEY in Cloud Run environment variables."
            )
```

---

## 🧪 Verification

**Test locally (development):**
```bash
# Should work without SECRET_KEY in development
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**Test in production (Cloud Run):**
```bash
# Must set SECRET_KEY env var
gcloud run deploy khasyaraka \
  --source . \
  --set-env-vars SECRET_KEY="your-secret-key-here" \
  --set-env-vars DATABASE_URL="your-db-url" \
  --set-env-vars REDIS_URL="your-redis-url" \
  --set-env-vars ENVIRONMENT="production"
```

---

## 🚀 Required Cloud Run Environment Variables

**CRITICAL - Must be set:**

1. **SECRET_KEY** - JWT signing key (required)
   ```bash
   # Generate a secure key:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **DATABASE_URL** - Supabase connection string
   ```
   postgresql://user:pass@host:port/dbname
   ```

3. **REDIS_URL** - Redis connection string
   ```
   redis://host:port or rediss://host:port (for TLS)
   ```

4. **ENVIRONMENT** - Set to `production`

---

## 📝 Why This Fix Works

1. **Pydantic Field Validation:**
   - `Field(...)` = Required, fails immediately if missing
   - `Field(default="")` = Optional, allows Settings() to initialize

2. **Custom Validation:**
   - `model_post_init()` runs after Pydantic field validation
   - Can provide better error messages
   - Can check environment context (production vs development)

3. **Graceful Degradation:**
   - Development: Works without SECRET_KEY (for local testing)
   - Production: Validates and fails with clear error message

---

## 🔍 Troubleshooting

**If you still get ValidationError:**

1. **Check Cloud Run environment variables:**
   ```bash
   gcloud run services describe khasyaraka --region asia-southeast2
   ```

2. **Set SECRET_KEY:**
   ```bash
   gcloud run services update khasyaraka \
     --region asia-southeast2 \
     --set-env-vars SECRET_KEY="your-secret-key"
   ```

3. **Verify all required vars:**
   ```bash
   gcloud run services update khasyaraka \
     --region asia-southeast2 \
     --set-env-vars SECRET_KEY="..." \
     --set-env-vars DATABASE_URL="..." \
     --set-env-vars REDIS_URL="..." \
     --set-env-vars ENVIRONMENT="production"
   ```

---

**Status:** ✅ Fixed - Settings can initialize, validation happens in model_post_init()
