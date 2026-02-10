# 🔄 Update Flutter App untuk Service Baru

**Status:** Service lama (`khasyaraka`) masih disabled, service baru (`khasyaraka-v2`) sedang dibuat.

---

## 📋 **Langkah-langkah:**

### **Step 1: Tunggu Service Baru Selesai Deploy**

1. **Buka:** https://console.cloud.google.com/run/services?project=scout-os-dev
2. **Cari:** Service `khasyaraka-v2`
3. **Tunggu:** Status menjadi **"Active"** atau **"Ready"**
4. **Copy:** URL endpoint baru (akan seperti: `https://khasyaraka-v2-890949539640.asia-southeast2.run.app`)

---

### **Step 2: Update Flutter App**

Setelah service baru aktif, update `environment.dart`:

**File:** `scout_os_app/lib/core/config/environment.dart`

**Current (Service Lama):**
```dart
static const String apiBaseUrl = "https://khasyaraka-890949539640.asia-southeast2.run.app/api/v1";
```

**Update ke (Service Baru):**
```dart
static const String apiBaseUrl = "https://khasyaraka-v2-890949539640.asia-southeast2.run.app/api/v1";
```

**⚠️ PENTING:** Ganti `khasyaraka` dengan `khasyaraka-v2` di URL.

---

### **Step 3: Rebuild Flutter App**

```bash
cd scout_os_app
flutter clean
flutter pub get
flutter run
```

---

## 🎯 **Alternatif: Fix Service Lama**

Jika ingin tetap menggunakan service lama:

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Klik:** **EDIT & DEPLOY NEW REVISION**
3. **Update:** `DATABASE_URL` ke format `postgresql+asyncpg://...`
4. **Deploy**
5. **Trigger request** untuk wake up service

---

## ✅ **Checklist:**

- [ ] Service baru (`khasyaraka-v2`) sudah aktif
- [ ] Copy URL endpoint baru
- [ ] Update `environment.dart` dengan URL baru
- [ ] Rebuild Flutter app
- [ ] Test login/API calls

---

**Tunggu service baru selesai deploy, lalu update Flutter app dengan URL baru!** 🚀
