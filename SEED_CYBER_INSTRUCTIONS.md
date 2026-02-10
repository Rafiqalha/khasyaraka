# 🌱 Instruksi Seed Cyber Modules

## 📊 Status Data

- **File JSON:** `app/data/cyber_modules.json` memiliki **15 modules**
- **Endpoint `/cyber/seed`:** Hanya menambahkan **5 modules** (hardcoded)
- **Script `seed_cyber_data.py`:** Menggunakan data dari JSON (**15 modules**)

## ✅ Rekomendasi: Gunakan Script Python

Script `seed_cyber_data.py` lebih lengkap karena menggunakan data dari JSON file.

### **Cara Seed Data:**

```bash
cd scout_os_backend
python seed_cyber_data.py
```

Script ini akan:
1. ✅ Membaca `app/data/cyber_modules.json` (15 modules)
2. ✅ Membaca challenge files dari `app/data/cyber/*.json`
3. ✅ Insert ke database (update jika sudah ada)

---

## 🔄 Alternatif: Gunakan Endpoint API

Jika ingin seed via API (hanya 5 modules):

```bash
# Seed via API endpoint
curl -X POST "https://khasyaraka-v2-890949539640.asia-southeast2.run.app/api/v1/cyber/seed" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# Atau dengan force (jika sudah ada data)
curl -X POST "https://khasyaraka-v2-890949539640.asia-southeast2.run.app/api/v1/cyber/seed" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

**Catatan:** Endpoint ini hanya menambahkan 5 modules (Caesar, Morse, Atbash, Binary, Reverse).

---

## 📋 Modules yang Akan Di-Seed (dari JSON)

1. **mod_morse** - Audio Protocol (Sandi Morse)
2. **mod_angka** - Numeric Hash (Sandi Angka)
3. **mod_abjad** - Voice Auth Protocol (Sandi Abjad Inter)
4. **mod_kotak1** - Geo-Lock Grid (Sandi Kotak 1)
5. **mod_rumput** - Spectrum Analysis (Sandi Rumput)
6. **mod_semaphore** - Vector Signaling (Semaphore)
7. **mod_coord** - Matrix Coordinates (Sandi Merah Putih)
8. **mod_ular** - Serpentine Routing (Sandi Ular)
9. **mod_napoleon** - Block Transposition (Sandi Napoleon)
10. **mod_jepang** - Vertical Stack Processing (Sandi Jepang)
11. **mod_siput** - Vortex Algorithm (Sandi Siput)
12. **mod_an** - Mirror Encryption (Sandi AN/AZ)
13. **mod_sisipan** - Noise Filtering (Sandi Sisipan)
14. **mod_kurung** - Syntax Logic (Sandi Kurung)
15. **mod_sungai** - Cross-Stream Bridge (Sandi Sungai)

---

## ✅ Verifikasi Setelah Seed

```bash
# Cek via API
curl "https://khasyaraka-v2-890949539640.asia-southeast2.run.app/api/v1/cyber/modules"
```

Seharusnya mengembalikan:
```json
{
  "total": 15,
  "modules": [...]
}
```

---

## 🎯 Langkah Selanjutnya

1. **Jalankan script seed:**
   ```bash
   cd scout_os_backend
   python seed_cyber_data.py
   ```

2. **Restart aplikasi Flutter**

3. **Buka halaman cyber** - seharusnya sudah muncul 15 modules
