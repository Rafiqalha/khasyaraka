# Sandi Pramuka Module Implementation

## Overview

Implementasi modul **Cyber/Sandi Pramuka** untuk platform Scout OS. Modul ini memungkinkan pengguna mempelajari 15 jenis Sandi Pramuka dengan pendekatan Cyber Security.

## Architecture

### 1. Database Models (`app/modules/cyber/models.py`)

#### `SandiType`
- Menyimpan metadata untuk 15 jenis cipher
- Fields: `id`, `codename`, `name`, `description`, `difficulty`, `category`
- Categories: `encoding`, `substitution`, `transposition`, `visual`

#### `SandiQuestion`
- Menyimpan soal ujian untuk setiap Sandi
- Fields: `id`, `sandi_id`, `question_text`, `encrypted_text`, `correct_answer`, `hint`, `difficulty`, `xp_reward`

#### `EncryptionLog`
- Audit trail untuk penggunaan Tool Mode
- Fields: `id`, `user_id`, `sandi_id`, `input_hash`, `operation_mode`, `timestamp`

### 2. Pydantic Schemas (`app/modules/cyber/schemas.py`)

- `SandiBase`, `SandiCreate`, `SandiResponse` - Untuk Sandi Type
- `SandiListResponse` - Response untuk list Sandi
- `CyberToolRequest` - Request untuk encryption/decryption
- `CyberToolResponse` - Response hasil encryption/decryption
- `SandiQuestionResponse` - Response untuk soal ujian
- `SandiExamResponse` - Response untuk exam questions

### 3. Cipher Service (`app/modules/cyber/cipher_service.py`)

#### Factory Pattern Implementation

**Abstract Base Class:**
- `BaseCipher` - Abstract class dengan methods `encrypt()` dan `decrypt()`

**Implemented Ciphers:**
- `MorseCipher` - Implementasi Morse Code (✅ Complete)
- `AnRot13Cipher` - Implementasi ROT13/Caesar Cipher (✅ Complete)
- `PlaceholderCipher` - Placeholder untuk cipher yang belum diimplementasikan

**Factory:**
- `CipherFactory` - Factory class untuk membuat cipher instance berdasarkan codename
- Method `create_cipher(sandi_type)` - Returns cipher instance
- Method `register_cipher(codename, cipher_class)` - Register cipher baru

### 4. Service Layer (`app/modules/cyber/service.py`)

#### Methods:
- `get_all_sandi_types()` - Get semua Sandi types
- `process_cipher_tool(user_id, request)` - Process encryption/decryption dengan audit logging
- `get_sandi_exam(sandi_id, limit)` - Get random exam questions

### 5. Repository Layer (`app/modules/cyber/repository.py`)

#### Methods:
- `get_all_sandi_types()` - Query semua Sandi types
- `get_sandi_by_codename(codename)` - Get Sandi by codename
- `get_sandi_by_id(sandi_id)` - Get Sandi by ID
- `get_random_sandi_questions(sandi_id, limit)` - Get random questions
- `create_encryption_log(...)` - Create audit log entry

### 6. API Router (`app/modules/cyber/router.py`)

#### Endpoints:

**GET `/cyber/list`**
- Returns: List of 15 Sandi types
- Response: `SandiListResponse`

**POST `/cyber/tool/process`**
- Request: `CyberToolRequest` (text, operation_mode, sandi_codename)
- Response: `CyberToolResponse` (result, sandi_codename, operation_mode)
- Auth: Required (JWT)
- Features: 
  - Encrypt/Decrypt text
  - Audit logging (EncryptionLog)

**GET `/cyber/exam/{sandi_id}`**
- Query params: `limit` (default: 5, max: 20)
- Response: `SandiExamResponse` (questions list)
- Returns: Random exam questions for Sandi type

### 7. Data Seeding (`seed_sandi_data.py`)

Script untuk seed 15 Sandi types ke database:

```bash
cd scout_os_backend
python seed_sandi_data.py
```

**15 Sandi Types:**
1. Morse (encoding, difficulty: 1)
2. Semaphore (visual, difficulty: 2)
3. Rumput (visual, difficulty: 2)
4. Kimia (substitution, difficulty: 3)
5. Angka (substitution, difficulty: 1)
6. AN (ROT13) (substitution, difficulty: 1) ✅ Implemented
7. AZ (Atbash) (substitution, difficulty: 1)
8. Kotak 1 (transposition, difficulty: 2)
9. Kotak 2 (transposition, difficulty: 2)
10. Kotak 3 (transposition, difficulty: 3)
11. Jam (visual, difficulty: 2)
12. Koordinat (substitution, difficulty: 2)
13. AND (substitution, difficulty: 3)
14. Ular (transposition, difficulty: 2)
15. Napoleon (transposition, difficulty: 3)

## Usage Examples

### 1. Get All Sandi Types

```bash
curl -X GET "http://localhost:8000/api/cyber/list" \
  -H "Authorization: Bearer <token>"
```

### 2. Encrypt Text (Morse)

```bash
curl -X POST "http://localhost:8000/api/cyber/tool/process" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "HELLO WORLD",
    "operation_mode": "ENCRYPT",
    "sandi_codename": "morse"
  }'
```

Response:
```json
{
  "result": ".... . .-.. .-.. --- / .-- --- .-. .-.. -..",
  "sandi_codename": "morse",
  "operation_mode": "ENCRYPT"
}
```

### 3. Decrypt Text (ROT13)

```bash
curl -X POST "http://localhost:8000/api/cyber/tool/process" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "URYYB",
    "operation_mode": "DECRYPT",
    "sandi_codename": "an_rot13"
  }'
```

Response:
```json
{
  "result": "HELLO",
  "sandi_codename": "an_rot13",
  "operation_mode": "DECRYPT"
}
```

### 4. Get Exam Questions

```bash
curl -X GET "http://localhost:8000/api/cyber/exam/1?limit=5" \
  -H "Authorization: Bearer <token>"
```

## Database Migration

Setelah implementasi, jalankan Alembic migration:

```bash
cd scout_os_backend
alembic revision --autogenerate -m "Add Sandi Pramuka models"
alembic upgrade head
```

## Next Steps

### 1. Implement Remaining Ciphers

Saat ini hanya 2 cipher yang fully implemented:
- ✅ Morse
- ✅ AN (ROT13)

**To Implement:**
- Semaphore
- Rumput
- Kimia
- Angka
- AZ (Atbash)
- Kotak 1, 2, 3
- Jam
- Koordinat
- AND
- Ular
- Napoleon

**How to Add:**
1. Create new class inheriting `BaseCipher`
2. Implement `encrypt()` and `decrypt()` methods
3. Register in `CipherFactory._cipher_classes` or use `register_cipher()`

### 2. Add Exam Questions

Seed database dengan `SandiQuestion` data untuk setiap Sandi type.

### 3. Frontend Integration

Integrate dengan Flutter app:
- Display Sandi list
- Tool Mode UI (encrypt/decrypt)
- Exam Mode UI (questions & answers)

## File Structure

```
scout_os_backend/
├── app/
│   └── modules/
│       └── cyber/
│           ├── models.py          # SandiType, SandiQuestion, EncryptionLog
│           ├── schemas.py         # Pydantic schemas
│           ├── cipher_service.py  # Factory pattern + cipher implementations
│           ├── service.py         # Business logic
│           ├── repository.py      # Database access
│           └── router.py          # API endpoints
├── seed_sandi_data.py             # Seeding script
└── SANDI_MODULE_IMPLEMENTATION.md # This file
```

## Testing

### Manual Testing

1. **Seed Data:**
   ```bash
   python seed_sandi_data.py
   ```

2. **Test Endpoints:**
   - Use FastAPI docs: `http://localhost:8000/docs`
   - Or use curl commands above

3. **Verify Database:**
   ```sql
   SELECT * FROM sandi_types;
   SELECT * FROM encryption_logs;
   ```

## Notes

- All cipher operations are logged in `EncryptionLog` for audit trail
- Input text is hashed (SHA-256) before logging for privacy
- Factory pattern allows easy extension for new ciphers
- Placeholder cipher returns "[Not Implemented]" for unimplemented types

---

**Last Updated:** February 2026
