from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.training.router import router as training_router
from app.modules.cyber.router import router as cyber_router
from app.modules.sku.router import router as sku_router
from app.modules.survival.router import router as survival_router
from app.modules.gamification.router import router as leaderboard_router
from app.modules.admin.router import router as admin_router
from app.api.endpoints.user_cache import router as user_cache_router
from app.api.endpoints.callbacks import router as callbacks_router
from app.modules.tkk.router import router as tkk_router
from app.modules.subscription.router import router as subscription_router

api_router = APIRouter()

# Sambungkan auth router ke jalur utama
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Sambungkan users router
api_router.include_router(users_router)

# Sambungkan training router ke jalur utama
# Note: training_router already has prefix="/training" defined, so we don't add it again
api_router.include_router(training_router)
api_router.include_router(cyber_router)
api_router.include_router(sku_router, prefix="/sku", tags=["SKU"])
api_router.include_router(survival_router, prefix="/survival", tags=["Survival"])
api_router.include_router(tkk_router)

# Sambungkan leaderboard router
api_router.include_router(leaderboard_router)

# ✅ NEW: User Cache endpoints (Cache-Aside + Write-Behind)
api_router.include_router(user_cache_router)

# ✅ NEW: Callbacks (AdMob SSV, etc.)
api_router.include_router(callbacks_router)

# ✅ Subscription management
api_router.include_router(subscription_router, prefix="/user", tags=["Subscription"])

# ✅ ADMIN: Protected admin endpoints (reset-world, etc.)
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])