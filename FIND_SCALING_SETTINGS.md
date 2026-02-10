# 🔍 Cara Menemukan Scaling Settings di Cloud Run

**Masalah:** Tidak menemukan opsi "Automatic" atau "Manual" untuk scaling

**Kemungkinan:** Scaling settings ada di tab lain atau perlu di-expand

---

## 📋 **Lokasi Scaling Settings**

### **Method 1: Tab "General" atau "Configuration"**

1. Di halaman **"Deploy revision"**, cari tab di atas:
   - **"Containers"** (yang sedang kamu lihat)
   - **"Networking"**
   - **"Security"**
   - **"General"** atau **"Configuration"** ← **CEK TAB INI!**

2. **Klik tab "General"** atau **"Configuration"**
3. Scroll ke bawah, cari section **"Scaling"** atau **"Autoscaling"**

---

### **Method 2: Expand Advanced Settings**

1. Di halaman **"Deploy revision"**, scroll ke bawah
2. Cari tombol **"Show advanced settings"** atau **"Advanced"**
3. **Klik** untuk expand
4. Cari section **"Scaling"** atau **"Autoscaling"**

---

### **Method 3: Via Service Details (Bukan Deploy Page)**

1. **Kembali ke Service Details:**
   - Klik **"←"** (back arrow) di kiri atas
   - Atau buka: https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka

2. **Klik:** **"EDIT & DEPLOY NEW REVISION"**

3. **Di halaman edit, cari:**
   - Tab **"General"** atau **"Configuration"**
   - Section **"Scaling"** atau **"Autoscaling"**
   - Dropdown/Radio button untuk pilih scaling mode

---

## 🔍 **Visual Guide: Di Mana Scaling Settings?**

**Di halaman "Deploy revision", cari:**

```
┌─────────────────────────────────────┐
│ Tabs:                                │
│ [Containers] [Networking] [Security]│
│         ↑                            │
│    Cek tab lain!                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Atau scroll ke bawah:                │
│ ...                                  │
│ [Show advanced settings] ← Klik ini! │
│ ...                                  │
│ Scaling: [Manual ▼] ← Di sini!      │
└─────────────────────────────────────┘
```

---

## 🎯 **Alternatif: Set via Environment Variables Dulu**

Sambil mencari scaling settings, pastikan dulu **DATABASE_URL** sudah benar:

### **Step 1: Update DATABASE_URL**

1. Di halaman **"Deploy revision"**
2. Tab **"Containers"** → Sub-tab **"Variables & Secrets"**
3. Find **`DATABASE_URL`**
4. **Update Value:**
   ```
   postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
   **⚠️ PENTING:** Pastikan ada `+asyncpg` setelah `postgresql`

---

## 🔍 **Cara Lain: Cek di Service Details**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Scroll ke bawah** di halaman Service Details
3. Cari section **"Scaling"** atau **"Autoscaling"**
4. Jika ada tombol **"Edit"** atau **"Change"**, klik itu

---

## 📋 **Checklist**

- [ ] Cek semua tab di halaman Deploy (General, Configuration, dll)
- [ ] Scroll ke bawah, cari "Show advanced settings"
- [ ] Cek di Service Details page (bukan Deploy page)
- [ ] Update DATABASE_URL dulu (di tab Variables & Secrets)
- [ ] Setelah itu, cari scaling settings

---

## 💡 **Tips**

- Scaling settings biasanya ada di **tab "General"** atau **"Configuration"**
- Atau perlu klik **"Show advanced settings"** untuk melihatnya
- Atau ada di **Service Details page** (bukan Deploy page)

---

**Coba cek tab "General" atau scroll ke bawah cari "Show advanced settings"!** 🔍
