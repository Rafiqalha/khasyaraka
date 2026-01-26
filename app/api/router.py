from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.training.router import router as training_router
from app.modules.cyber.router import router as cyber_router
from app.modules.sku.router import router as sku_router
from app.modules.survival.router import router as survival_router
from app.modules.gamification.router import router as leaderboard_router

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

# Sambungkan leaderboard router
api_router.include_router(leaderboard_router)