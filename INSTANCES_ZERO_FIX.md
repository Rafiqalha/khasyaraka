# 🔍 Diagnosa: Instances: 0 (Container Tidak Running)

**Status dari Screenshot:**
- ✅ Deployment: Completed (semua step sukses)
- ✅ Service: Active
- ❌ **Instances: 0** (tidak ada container running)
- ❌ Metrics: No data (karena tidak ada request/instances)

---

## 🔍 Kemungkinan Penyebab

### **1. Container Crash Saat Startup (Paling Mungkin)**
- Environment variables masih salah
- Application error saat startup
- Database/Redis connection failed

### **2. Scale to Zero (Normal untuk Cloud Run)**
- Cloud Run bisa scale to zero jika tidak ada traffic
- Container akan start otomatis saat ada request pertama
- Tapi jika crash, akan tetap 0 instances

### **3. Health Check Failed**
- Container start tapi health check gagal
- Service di-mark sebagai unhealthy

---

## 🛠️ SOLUSI: Cek Logs untuk Error Spesifik

### **Step 1: Buka Logs**

1. Di Cloud Run Console, klik tab **LOGS** (bukan "Observability")
2. Atau langsung: https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka/logs
3. Filter: **Error** atau **Warning**
4. Cari error spesifik

---

### **Step 2: Common Errors & Fixes**

#### **A. ValidationError (Environment Variables)**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error
Field required [type=missing, input_value=None]
```
**Fix:** Pastikan semua env vars di-set:
- `ENVIRONMENT=production`
- `SECRET_KEY` (bukan placeholder)
- `DATABASE_URL` (format benar)
- `REDIS_URL` (format benar)

---

#### **B. ConnectionError (Database/Redis)**
```
ConnectionError: Failed to connect to Redis
OperationalError: connection failed
```
**Fix:** 
- Cek format `REDIS_URL` (`rediss://...` untuk TLS)
- Cek format `DATABASE_URL` (`postgresql+asyncpg://...`)
- Pastikan credentials benar

---

#### **C. ModuleNotFoundError**
```
ModuleNotFoundError: No module named 'xxx'
```
**Fix:** Cek `requirements.txt` lengkap

---

## 🧪 Test: Trigger Request untuk Wake Up Service

Cloud Run bisa scale to zero. Coba trigger request:

```bash
# Test health endpoint
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health

# Atau root endpoint
curl https://khasyaraka-890949539640.asia-southeast2.run.app/
```

**Expected:**
- Jika container start: `200 OK` dengan JSON response
- Jika container crash: `503 Service Unavailable` atau timeout

---

## 📋 Checklist Troubleshooting

- [ ] Cek **LOGS** tab (bukan Observability)
- [ ] Filter: **Error** atau **Warning**
- [ ] Cari error spesifik (ValidationError, ConnectionError, dll)
- [ ] Verifikasi environment variables di tab **Revisions**
- [ ] Test endpoint untuk trigger container start
- [ ] Jika masih error, fix berdasarkan error di logs

---

## 🎯 Action Items

1. **Cek Logs** - Tab LOGS, filter Error/Warning
2. **Copy error message** yang muncul
3. **Fix berdasarkan error** (env vars, connection, dll)
4. **Redeploy** setelah fix
5. **Test endpoint** untuk trigger container start

---

## 💡 Quick Fix: Verifikasi Environment Variables

**Via Console:**
1. Tab **REVISIONS**
2. Klik revision terbaru
3. Scroll ke **Environment Variables**
4. Pastikan semua ada:
   - ✅ `ENVIRONMENT=production`
   - ✅ `SECRET_KEY` (bukan placeholder)
   - ✅ `DATABASE_URL` (format `postgresql+asyncpg://...`)
   - ✅ `REDIS_URL` (format `rediss://...`)

---

**Cek LOGS tab untuk melihat error spesifik!** 🔍
