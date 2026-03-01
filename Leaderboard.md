# 🏆 Real-Time Leaderboard Service — Analisis Kompleksitas Algoritma

> Dokumentasi ini menjelaskan bagaimana sistem leaderboard bekerja secara efisien menggunakan **Redis Sorted Set** sebagai cache utama dan **PostgreSQL** sebagai fallback — lengkap dengan analisis kompleksitas algoritmanya.

---

## 📖 Daftar Isi

- [Gambaran Umum Sistem](#-gambaran-umum-sistem)
- [Komponen Kompleksitas](#-komponen-kompleksitas)
- [Notasi Big-O yang Digunakan](#-notasi-big-o-yang-digunakan)
- [Hierarki Kecepatan Operasi](#-hierarki-kecepatan-operasi)
- [Skenario Analisis Kasus](#-skenario-analisis-kasus)
- [Istilah Penting](#-istilah-penting)

---

## 🔭 Gambaran Umum Sistem

Sistem leaderboard ini menggunakan dua lapisan penyimpanan data:

```
Request masuk
     │
     ▼
┌─────────────────────┐
│   Redis (ZSET)      │  ← Cache utama di RAM, super cepat
│   In-Memory Cache   │
└─────────┬───────────┘
          │ Cache miss / kosong?
          ▼
┌─────────────────────┐
│   PostgreSQL DB     │  ← Fallback ke disk, lebih lambat tapi persisten
│   Persistent Store  │
└─────────────────────┘
```

**Intinya:** selama Redis punya datanya, sistem berjalan sangat cepat. Kalau Redis kosong (misalnya server baru nyala), baru deh ambil dari PostgreSQL sambil isi ulang cache Redis.

---

## 🧩 Komponen Kompleksitas

### Ukuran Input

| Simbol | Arti | Contoh |
|--------|------|--------|
| **N** | Jumlah total pengguna aktif di sistem | 1.000.000 user terdaftar |
| **M** | Jumlah data yang ditampilkan sekaligus | Top 10 / Top 100 di layar |

### Dua Jenis Kompleksitas

**⏱️ Kompleksitas Waktu** — Seberapa cepat sistem merespons saat jumlah pengguna bertambah.

**💾 Kompleksitas Ruang** — Seberapa banyak memori tambahan yang dipakai. Sistem ini butuh `O(N)` memori di Redis, karena setiap user punya satu entri berisi `user_id` + total XP-nya.

---

## 📐 Notasi Big-O yang Digunakan

| Notasi | Nama | Artinya dalam konteks ini |
|--------|------|--------------------------|
| `O(f(n))` | **Big-O** | Batas atas — performa terburuk yang mungkin terjadi |
| `Ω(f(n))` | **Big-Omega** | Batas bawah — performa terbaik yang bisa dicapai |
| `Θ(f(n))` | **Big-Theta** | Batas ketat — performa normal rata-rata yang konsisten |

---

## ⚡ Hierarki Kecepatan Operasi

Berikut semua operasi dalam sistem, diurutkan dari yang paling cepat:

### 1. `O(1)` — Konstan *(Secepat kilat)*

**Operasi:** Menghitung total jumlah pengguna di leaderboard (`Redis ZCARD`)

```
ZCARD leaderboard  →  langsung dapat angkanya, tanpa peduli N sebesar apapun
```

> 💡 Bayangkan kamu punya toples berisi kelereng dan kamu sudah menghitung jumlahnya di label luar. Mau ada 10 atau 10 juta kelereng, cukup lihat label — jawabannya instan.

---

### 2. `O(log N)` — Logaritmik *(Sangat cepat, skala baik)*

**Operasi:** Tambah/update XP user (`ZADD`), cari posisi ranking user (`ZREVRANK`)

```
N = 1.000 user    →  ~10 langkah
N = 1.000.000 user →  ~20 langkah   (naik 1000x user, tapi cuma +10 langkah!)
```

Redis menggunakan struktur data **Skip List** secara internal — mirip buku telepon yang kamu bisa loncat ke bagian tertentu tanpa baca dari awal.

> 💡 Ini seperti tebak angka 1–100. Coba 50 dulu, terlalu kecil? Coba 75. Terlalu besar? Coba 62. Hanya butuh ~7 tebakan — jauh lebih efisien dari cek satu-satu.

---

### 3. `O(M)` — Linear terhadap M *(Cukup cepat)*

**Operasi:** Ambil daftar Top-M dari Redis, lalu lengkapi detail profil tiap user

```
Ambil Top 10  →  10 langkah
Ambil Top 100 →  100 langkah
```

Ini wajar — kalau mau tampilkan 100 user, ya harus proses 100 data. Yang penting M-nya kecil dan dibatasi oleh parameter `limit`.

---

### 4. `O(N log N)` atau `O(M log N)` — Linearitmik *(Fallback, lebih lambat)*

**Operasi:** Query PostgreSQL saat Redis kosong (`SELECT ... ORDER BY total_xp DESC`)

```sql
SELECT user_id, total_xp FROM xp_logs ORDER BY total_xp DESC LIMIT M;
```

Database harus **mengurutkan semua data** sebelum bisa ambil top-M. Kalau sudah ada index di kolom `total_xp`, bisa dipangkas jadi `O(M log N)`.

> ⚠️ Inilah kenapa Redis penting — mencegah operasi mahal ini terjadi setiap request.

---

### ✅ Yang Berhasil Dihindari

| Kompleksitas | Kenapa Berbahaya | Status |
|---|---|---|
| `O(N²)` — Kuadratik | 1 juta user = 1 triliun operasi | ✅ Dihindari |
| `O(2ⁿ)` — Eksponensial | Tidak skalabel sama sekali | ✅ Dihindari |
| `O(N!)` — Faktorial | Mustahil untuk N besar | ✅ Dihindari |

---

## 🎭 Skenario Analisis Kasus

### 🥇 Best Case — Redis Cache 100% Hit

**Kondisi:** Data leaderboard sudah ada di Redis (kondisi normal sehari-hari)

| Operasi | Kompleksitas |
|---------|-------------|
| Ambil posisi rank user | `Ω(log N)` |
| Hitung total peserta | `Ω(1)` |
| Ambil Top-M leaderboard | `Ω(M)` |

**Hasil:** Respons dalam hitungan milidetik, bahkan untuk jutaan pengguna.

---

### ⚖️ Average Case — Operasi Normal Top-M

**Kondisi:** Request rutin ambil Top-10 / Top-50 dari Redis yang sudah terisi

```
Kompleksitas total: Θ(log N + M)
```

- `log N` → cari posisi awal di sorted set
- `M` → iterasi dan petakan M data ke response

**Hasil:** Stabil dan konsisten di semua kondisi normal.

---

### 🥶 Worst Case — Cold Start (Redis Kosong)

**Kondisi:** Server baru nyala, Redis belum punya data. Semua request jatuh ke PostgreSQL.

```
Kompleksitas total: O(N log N)
```

**Urutan kejadian:**
1. Redis kosong → tidak ada data
2. Query PostgreSQL dengan `ORDER BY` → `O(N log N)`
3. Hasil dimasukkan ke Redis secara massal (mass insert)
4. Request berikutnya sudah bisa ambil dari Redis

**Solusi:** Warm-up cache saat startup, atau gunakan persistent Redis (AOF/RDB snapshot).

---

### Ringkasan Perbandingan Kasus

```
Best Case    ──────── Ω(1) hingga Ω(log N)     ← Redis hit, super cepat
Average Case ──────── Θ(log N + M)              ← Normal operation
Worst Case   ──────── O(N log N)                ← Cold start, fallback ke DB
```

---

## 📚 Istilah Penting

| Istilah | Penjelasan Simpel |
|---------|------------------|
| **Redis ZSET** | Struktur data Redis yang menyimpan data terurut berdasarkan skor (XP) — operasi add & rank cuma O(log N) |
| **Skip List** | Struktur data internal Redis yang mirip linked list berlapis — bisa loncat, sehingga pencarian sangat efisien |
| **Cache Hit** | Redis punya data yang diminta — langsung balik, cepat |
| **Cache Miss** | Redis tidak punya data — harus ambil dari PostgreSQL, lebih lambat |
| **Cold Start** | Kondisi saat Redis baru menyala dan belum punya data sama sekali |
| **Fallback** | Mekanisme cadangan: kalau Redis gagal, sistem otomatis pakai PostgreSQL |
| **Asimptotik** | Cara menganalisis performa algoritma saat jumlah data mendekati sangat besar (N → ∞) |
| **Skalabilitas** | Kemampuan sistem tetap cepat meski jumlah pengguna bertambah drastis |
| **Iteratif vs Rekursif** | Sistem ini pakai loop biasa (iteratif), bukan rekursi — menghindari stack overflow untuk data besar |

---

## 🏗️ Arsitektur Keputusan

```
Kenapa Redis + PostgreSQL, bukan salah satu saja?

Redis saja:
  ✅ Super cepat
  ❌ Data hilang kalau server mati (volatile)

PostgreSQL saja:
  ✅ Data aman, persisten
  ❌ ORDER BY tiap request = lambat untuk data besar

Redis + PostgreSQL (Hybrid):
  ✅ Cepat (Redis handle hot data)
  ✅ Aman (PostgreSQL sebagai source of truth)
  ✅ Skalabel untuk jutaan pengguna
```

---

> **Kesimpulan:** Sistem leaderboard ini dirancang untuk skalabilitas ekstrem. Dengan Redis sebagai lapisan pertama, mayoritas operasi berjalan di `O(1)` hingga `O(log N)` — artinya sistem tetap responsif bahkan saat basis pengguna tumbuh dari ribuan menjadi jutaan.