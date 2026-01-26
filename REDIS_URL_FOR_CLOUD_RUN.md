# ✅ Redis URL untuk Cloud Run

**Source:** Upstash Redis  
**TLS:** Enabled (gunakan `rediss://`)

---

## 🔑 Redis Connection Details

**Host:** `finer-leech-56092.upstash.io`  
**Port:** `6379`  
**Password:** `AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI`  
**TLS:** Yes (Upstash requires TLS)

---

## 📋 Format REDIS_URL untuk Cloud Run

### **Dengan TLS (Recommended untuk Upstash):**
```
rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
```

**⚠️ PENTING:** Gunakan `rediss://` (dengan double 's') untuk TLS connection.

---

## 🚀 Set di Cloud Run

### **Via Console:**

1. Cloud Run → `khasyaraka` → **EDIT & DEPLOY NEW REVISION**
2. Tab **VARIABLES & SECRETS**
3. Add/Update variable:
   - **Name:** `REDIS_URL`
   - **Value:** `rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379`
4. **DEPLOY**

---

### **Via gcloud CLI:**

```bash
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars REDIS_URL="rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379"
```

---

## ✅ Complete Environment Variables Checklist

Pastikan semua ini di-set di Cloud Run:

- [ ] `ENVIRONMENT=production`
- [ ] `SECRET_KEY` = (generate dengan: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] `DATABASE_URL` = (Supabase connection string)
- [ ] `REDIS_URL` = `rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379`
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES=10080` (optional)

---

## 🧪 Test Redis Connection

**Local test (jika perlu):**
```bash
redis-cli --tls -u rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
```

**Expected:** Connected to Redis

---

## 📝 Notes

- **TLS Required:** Upstash Redis requires TLS, jadi harus pakai `rediss://`
- **Password:** Jangan expose password di public repos
- **Format:** `rediss://default:password@host:port`
- **Backend Support:** Backend sudah support `rediss://` (lihat `app/core/redis.py`)

---

**Set REDIS_URL ini di Cloud Run, lalu redeploy!** 🚀
