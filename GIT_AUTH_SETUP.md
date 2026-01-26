# 🔐 Setup Git Authentication untuk GitHub

**Error:** `Authentication failed for 'https://github.com/Rafiqalha/khasyaraka.git/'`

---

## 🔧 SOLUSI: Setup Git Authentication

### **Opsi 1: Menggunakan Personal Access Token (Recommended)**

**Langkah 1: Buat Personal Access Token di GitHub**

1. Buka: https://github.com/settings/tokens
2. Klik "Generate new token" → "Generate new token (classic)"
3. Beri nama: `khasyaraka-dev`
4. Pilih scopes:
   - ✅ `repo` (Full control of private repositories)
5. Klik "Generate token"
6. **COPY TOKEN** (hanya muncul sekali!)

**Langkah 2: Setup Git Credential**

```bash
# Method 1: Set credential helper (akan menyimpan token)
git config --global credential.helper store

# Method 2: Atau gunakan cache (temporary)
git config --global credential.helper cache
git config --global credential.helper 'cache --timeout=3600'
```

**Langkah 3: Push dengan Token**

```bash
cd /home/rafiq/Projek/khasyaraka

# Push (akan prompt untuk username & password)
# Username: Rafiqalha
# Password: <paste-token-di-sini>
git push -u origin main
```

---

### **Opsi 2: Menggunakan SSH (Lebih Aman)**

**Langkah 1: Generate SSH Key**

```bash
# Generate SSH key (jika belum ada)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub
```

**Langkah 2: Add SSH Key ke GitHub**

1. Buka: https://github.com/settings/keys
2. Klik "New SSH key"
3. Paste public key
4. Klik "Add SSH key"

**Langkah 3: Ubah Remote URL ke SSH**

```bash
cd /home/rafiq/Projek/khasyaraka

# Ubah remote URL dari HTTPS ke SSH
git remote set-url origin git@github.com:Rafiqalha/khasyaraka.git

# Verify
git remote -v

# Push
git push -u origin main
```

---

### **Opsi 3: Menggunakan GitHub CLI (Paling Mudah)**

```bash
# Install GitHub CLI (jika belum ada)
# Ubuntu/Debian:
sudo apt install gh

# Login
gh auth login

# Pilih:
# - GitHub.com
# - HTTPS
# - Login with web browser (atau token)

# Push
git push -u origin main
```

---

## 🚀 QUICK FIX (Terminal)

**Jika ingin cepat, gunakan Personal Access Token:**

```bash
cd /home/rafiq/Projek/khasyaraka

# Set credential helper
git config --global credential.helper store

# Push (akan prompt untuk credentials)
git push -u origin main

# Saat prompt:
# Username: Rafiqalha
# Password: <paste-personal-access-token>
```

**Atau gunakan token langsung di URL:**

```bash
# Ganti YOUR_TOKEN dengan Personal Access Token
git remote set-url origin https://YOUR_TOKEN@github.com/Rafiqalha/khasyaraka.git

# Push
git push -u origin main
```

---

## ✅ VERIFIKASI

```bash
# Check remote URL
git remote -v

# Test connection
git ls-remote origin

# Push
git push -u origin main
```

---

## 🔐 SECURITY NOTES

**Jangan commit:**
- Personal Access Token
- SSH private keys
- `.env` files dengan secrets

**Sudah di-ignore oleh `.gitignore`:**
- ✅ `.env`
- ✅ `*.key`
- ✅ `*.pem`

---

**Pilih salah satu metode di atas untuk setup authentication!**
