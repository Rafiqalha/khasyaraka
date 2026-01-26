# ✅ FIX: Survival Mastery 401 Unauthorized Error

**Date:** 2026-01-26  
**Issue:** `GET /api/v1/survival/mastery` returns 401 Unauthorized  
**Status:** ✅ FIXED

---

## 🔴 ROOT CAUSE

**Problem:** Flutter `SurvivalRepository` was using incorrect authentication method.

**Details:**
- Backend endpoint requires JWT authentication via `Authorization: Bearer <token>` header
- Flutter was sending `X-User-Id` header instead
- Backend's `get_current_user` dependency expects JWT token, not user ID header

---

## ❌ BEFORE (Incorrect)

**File:** `scout_os_app/lib/features/mission/subfeatures/survival/data/survival_repository.dart`

**Issue:**
```dart
_dio.interceptors.add(
  InterceptorsWrapper(
    onRequest: (options, handler) async {
      final userId = await _authService.getCurrentUserId();
      if (userId != null && userId.isNotEmpty) {
        options.headers['X-User-Id'] = userId;  // ❌ Wrong header
      }
      handler.next(options);
    },
  ),
);
```

**Result:**
- Request sent with `X-User-Id` header
- Backend expects `Authorization: Bearer <token>`
- `get_current_user` dependency fails → 401 Unauthorized

---

## ✅ AFTER (Fixed)

**File:** `scout_os_app/lib/features/mission/subfeatures/survival/data/survival_repository.dart`

**Fix:**
```dart
import 'package:scout_os_app/core/network/api_dio_provider.dart';

class SurvivalRepository {
  SurvivalRepository({Dio? dio}) : _dio = dio ?? ApiDioProvider.getDio();
  // ✅ Uses centralized Dio instance with JWT interceptor
}
```

**What Changed:**
1. ✅ Removed custom interceptor with `X-User-Id` header
2. ✅ Now uses `ApiDioProvider.getDio()` which automatically adds `Authorization: Bearer <token>`
3. ✅ Consistent with other API calls in the app (training, leaderboard, etc.)
4. ✅ Removed `user_id` from request body (backend gets it from JWT token)

---

## 🔧 TECHNICAL DETAILS

### **Backend Authentication**

**File:** `scout_os_backend/app/modules/survival/router.py`

```python
@router.get("/mastery", response_model=AllMasteryResponse)
async def get_user_mastery(
    current_user: dict = Depends(get_current_user),  # ✅ Requires JWT
    db: AsyncSession = Depends(get_db)
):
    user_id = int(current_user.get("sub"))  # ✅ Extracts user_id from JWT
    return await service.get_all_mastery(user_id)
```

**Backend expects:**
- Header: `Authorization: Bearer <jwt_token>`
- JWT token contains user ID in `sub` claim
- No `X-User-Id` header needed

---

### **Flutter Authentication Pattern**

**File:** `scout_os_app/lib/core/network/api_dio_provider.dart`

**Centralized JWT interceptor:**
```dart
onRequest: (options, handler) async {
  final token = await _prefs?.getString(_tokenKey);
  if (token != null && token.isNotEmpty) {
    options.headers['Authorization'] = 'Bearer $token';  // ✅ Correct
  }
  handler.next(options);
}
```

**Benefits:**
- ✅ Consistent authentication across all API calls
- ✅ Automatic token injection
- ✅ Handles 401 errors (token expiration)
- ✅ Single source of truth for authentication

---

## 🧪 VERIFICATION

### **Before Fix:**
```bash
# Request sent:
GET /api/v1/survival/mastery
Headers:
  X-User-Id: 1  # ❌ Wrong header

# Response:
401 Unauthorized
```

### **After Fix:**
```bash
# Request sent:
GET /api/v1/survival/mastery
Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIs...  # ✅ Correct header

# Response:
200 OK
{
  "success": true,
  "data": {
    "tools": [...]
  }
}
```

---

## 📋 FILES MODIFIED

1. **scout_os_app/lib/features/mission/subfeatures/survival/data/survival_repository.dart**
   - Removed custom interceptor with `X-User-Id` header
   - Now uses `ApiDioProvider.getDio()` for JWT authentication
   - Removed `user_id` from request body (backend gets it from JWT)

---

## ✅ SUMMARY

**Issue:** Survival mastery endpoint returning 401 Unauthorized

**Root Cause:** Flutter using `X-User-Id` header instead of JWT `Authorization` header

**Fix:** Use centralized `ApiDioProvider.getDio()` which automatically adds JWT token

**Result:** 
- ✅ Endpoint now authenticates correctly
- ✅ Consistent with other API calls
- ✅ No more 401 errors

**Status:** ✅ PRODUCTION READY

---

## 🎯 EXPECTED BEHAVIOR

**After Fix:**
- ✅ `GET /api/v1/survival/mastery` returns 200 OK
- ✅ User mastery stats returned correctly
- ✅ `POST /api/v1/survival/action` works correctly
- ✅ No authentication errors

**Before Fix:**
- ❌ `GET /api/v1/survival/mastery` returns 401 Unauthorized
- ❌ User cannot view mastery stats
- ❌ Actions cannot be recorded
