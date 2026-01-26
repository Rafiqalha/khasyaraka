# 🚨 Service Status: 503 Service Unavailable

**URL:** https://khasyaraka-890949539640.asia-southeast2.run.app  
**Status:** ❌ **503 Service Unavailable - Service is disabled**

---

## 🔍 Diagnosa

**Error:** `503 Service Unavailable - Service is disabled`

**Kemungkinan Penyebab:**
1. **Container tidak bisa start** (masih ada masalah dengan environment variables atau code)
2. **Service disabled** (perlu di-enable)
3. **No instances running** (container crash saat startup)

---

## 🛠️ Solusi

### **Step 1: Cek Status Service**

```bash
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(status.conditions)"
```

**Cari:**
- `Ready: False` = Container tidak bisa start
- `Ready: True` = Container sudah start tapi service disabled

---

### **Step 2: Cek Environment Variables**

```bash
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(spec.template.spec.containers[0].env)"
```

**Pastikan:**
- ✅ `SECRET_KEY` bukan placeholder
- ✅ `REDIS_URL` ada dan format benar
- ✅ `DATABASE_URL` ada dan format benar
- ✅ `ENVIRONMENT=production`

---

### **Step 3: Cek Application Logs**

```bash
gcloud run services logs read khasyaraka \
  --region asia-southeast2 \
  --limit 50
```

**Cari error:**
- `ValidationError` = Environment variables tidak valid
- `ModuleNotFoundError` = Dependencies kurang
- `ConnectionError` = Database/Redis tidak bisa connect

---

### **Step 4: Enable Service (Jika Disabled)**

Jika service disabled:

```bash
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --no-traffic
```

Atau via Console:
1. Cloud Run → `khasyaraka`
2. Klik **ENABLE** (jika ada tombol)

---

### **Step 5: Fix Environment Variables (Jika Masih Placeholder)**

Jika `SECRET_KEY` masih placeholder atau `REDIS_URL` tidak ada:

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Update environment variables
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="$SECRET_KEY" \
  --set-env-vars REDIS_URL="redis://your-redis-host:port" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Redeploy
gcloud run deploy khasyaraka --source . --region asia-southeast2
```

---

### **Step 6: Force New Revision**

Jika masih error, force deploy revision baru:

```bash
gcloud run deploy khasyaraka \
  --source . \
  --region asia-southeast2 \
  --no-traffic \
  --tag test-revision
```

Kemudian assign traffic:

```bash
gcloud run services update-traffic khasyaraka \
  --region asia-southeast2 \
  --to-revisions test-revision=100
```

---

## 📋 Checklist Troubleshooting

- [ ] Cek status service (`gcloud run services describe`)
- [ ] Cek environment variables (pastikan tidak ada placeholder)
- [ ] Cek application logs (cari error spesifik)
- [ ] Enable service jika disabled
- [ ] Fix environment variables jika masih salah
- [ ] Redeploy setelah fix
- [ ] Test endpoint lagi

---

## 🎯 Expected Result

Setelah semua fix, endpoint harusnya merespons:

```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/

# Expected:
# {
#   "success": true,
#   "message": "API is healthy",
#   ...
# }
```

**Status:** 200 OK (bukan 503)

---

## 🔍 Quick Diagnostic Script

```bash
#!/bin/bash
echo "🔍 Cloud Run Service Diagnostic"
echo ""

echo "1. Service Status:"
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(status.conditions)"

echo ""
echo "2. Environment Variables:"
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(spec.template.spec.containers[0].env)"

echo ""
echo "3. Recent Logs (Errors):"
gcloud run services logs read khasyaraka \
  --region asia-southeast2 \
  --limit 20 | grep -E "(ERROR|WARNING|Exception)" | head -10

echo ""
echo "4. Test Endpoint:"
curl -s -w "\nHTTP: %{http_code}\n" https://khasyaraka-890949539640.asia-southeast2.run.app/
```

---

**Action:** Cek logs dan environment variables dulu untuk menemukan penyebab spesifik!
