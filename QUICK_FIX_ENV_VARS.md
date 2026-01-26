# 🚨 Quick Fix: Set Environment Variables untuk Cloud Run

**Error:** Container failed to start  
**Kemungkinan Penyebab:** Environment variables tidak di-set

---

## ⚡ Quick Fix Script

Jalankan script ini untuk set environment variables:

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Set environment variables (GANTI dengan nilai yang benar!)
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="$SECRET_KEY" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://user:pass@host:port/dbname" \
  --set-env-vars REDIS_URL="redis://host:port"

# Redeploy
gcloud run deploy khasyaraka --source . --region asia-southeast2
```

**⚠️ PENTING:** Ganti `DATABASE_URL` dan `REDIS_URL` dengan nilai yang benar!

---

## 📋 Environment Variables yang Diperlukan

### **1. ENVIRONMENT**
```
ENVIRONMENT=production
```

### **2. SECRET_KEY**
Generate dengan:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
Atau gunakan string random minimal 32 karakter.

### **3. DATABASE_URL**
Format Supabase:
```
postgresql+asyncpg://postgres.xxxxx:password@aws-0-asia-southeast2.pooler.supabase.com:6543/postgres
```
**Atau:**
```
postgresql+asyncpg://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

### **4. REDIS_URL**
Format Upstash atau Redis:
```
redis://default:password@host:port
```
**Atau dengan TLS:**
```
rediss://default:password@host:port
```

---

## 🔍 Verifikasi Environment Variables

Setelah set, verifikasi:

```bash
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(spec.template.spec.containers[0].env)"
```

---

## 🚀 Deploy Ulang

Setelah set environment variables:

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend
gcloud run deploy khasyaraka --source . --region asia-southeast2
```

---

## 📝 Checklist

- [ ] `ENVIRONMENT=production` di-set
- [ ] `SECRET_KEY` di-set (tidak kosong)
- [ ] `DATABASE_URL` di-set (format benar)
- [ ] `REDIS_URL` di-set (format benar)
- [ ] Redeploy setelah set env vars

---

**Setelah ini, cek log lagi untuk memastikan tidak ada error lain!**
