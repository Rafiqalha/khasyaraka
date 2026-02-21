from typing import List, Union
import os
from pydantic import AnyHttpUrl, PostgresDsn, RedisDsn, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- INFO APLIKASI ---
    PROJECT_NAME: str = "Scout OS (Khasyaraka)"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # --- SECURITY ---
    # ✅ SECRET_KEY: Optional at init, validated in model_post_init for production
    # This prevents Pydantic ValidationError during Settings() initialization
    # Validation happens in model_post_init() for production environments
    SECRET_KEY: str = Field(default="", description="JWT secret key (REQUIRED in production)")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 hari default
    
    # --- CORS (Penting buat Flutter) ---
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] | List[str] = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
        "*", # Hati-hati di production, tapi oke buat dev
    ]

    # --- POSTGRESQL ---
    # Option 1: Use full DATABASE_URL (recommended for Supabase)
    DATABASE_URL: Union[str, None] = None
    
    # Option 2: Use individual components (fallback if DATABASE_URL not provided)
    POSTGRES_SERVER: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_PORT: int = 5432
    
    SQLALCHEMY_DATABASE_URI: Union[str, None] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> AnyHttpUrl | str:
        # ✅ Priority 1: Use DATABASE_URL if provided (Supabase full URL)
        if isinstance(v, str):
            return v
        
        database_url = info.data.get("DATABASE_URL")
        if database_url:
            # ✅ Convert to asyncpg format if needed
            if database_url.startswith("postgresql://"):
                # Supabase Transaction Pooler uses postgresql://, convert to asyncpg
                return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif database_url.startswith("postgresql+asyncpg://"):
                return database_url
            else:
                # If already in correct format, return as-is
                return database_url
        
        # ✅ Priority 2: Build from individual components (fallback)
        # Validate that we have minimum required fields
        postgres_user = info.data.get("POSTGRES_USER")
        postgres_password = info.data.get("POSTGRES_PASSWORD")
        postgres_server = info.data.get("POSTGRES_SERVER")
        postgres_db = info.data.get("POSTGRES_DB")
        
        if not all([postgres_user, postgres_password, postgres_server, postgres_db]):
            raise ValueError(
                "Database configuration missing. "
                "Please set either DATABASE_URL (recommended for Supabase) "
                "or all of: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_SERVER, POSTGRES_DB"
            )
        
        # Kita pakai Driver asyncpg untuk performa tinggi
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=postgres_user,
            password=postgres_password,
            host=postgres_server,
            port=info.data.get("POSTGRES_PORT"),
            path=postgres_db,
        ).unicode_string()

    # --- IMAGEKIT (Avatar Storage) ---
    IMAGEKIT_PRIVATE_KEY: str = ""
    IMAGEKIT_PUBLIC_KEY: str = ""
    IMAGEKIT_URL_ENDPOINT: str = ""

    # --- REDIS ---
    # Support both REDIS_URL (full URL including rediss:// for TLS) and individual components
    REDIS_URL: Union[str, None] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Union[str, None] = None
    
    @property
    def REDIS_URL_COMPUTED(self) -> str:
        """Compute Redis URL from REDIS_URL or individual components"""
        if self.REDIS_URL:
            return self.REDIS_URL
        # Build from components (fallback)
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Konfigurasi untuk membaca environment variables
    # ✅ CRITICAL: In production, only read from env (not .env file)
    # Cloud Run sets env vars directly, no .env file exists
    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT", "development") != "production" else None,
        case_sensitive=True,
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        """
        Validate required variables after initialization.
        
        ✅ CRITICAL: Only validate in TRUE production (Cloud Run), not development with ENVIRONMENT=production.
        Detection: If .env file exists, we're in development (even if ENVIRONMENT=production).
        """
        # ✅ Only validate if this is TRUE production deployment (Cloud Run)
        # Detection: No .env file exists (Cloud Run doesn't have .env files)
        is_true_production = (
            self.ENVIRONMENT == "production" and
            not os.path.exists(".env")  # Cloud Run doesn't have .env files
        )
        
        if is_true_production:
            # Check DATABASE_URL or SQLALCHEMY_DATABASE_URI
            db_url = self.DATABASE_URL or self.SQLALCHEMY_DATABASE_URI
            if not db_url:
                print("🚨 CRITICAL: Missing DATABASE_URL in production. App will start in DEGRADED mode.")
                # Set dummy URL so SQLAlchemy engine creation doesn't crash at module import time
                # Connection attempts will fail gracefully with timeouts
                self.SQLALCHEMY_DATABASE_URI = "postgresql+asyncpg://error:error@localhost:5432/error_db"
            
            # Check REDIS_URL (only if no fallback to localhost)
            if not self.REDIS_URL and self.REDIS_HOST == "localhost":
                 print("🚨 CRITICAL: Missing REDIS_URL in production. App will start in DEGRADED mode.")
                 # Fallback to localhost (will likely fail connection, which is handled gracefully)
            
            # Check SECRET_KEY
            if not self.SECRET_KEY or self.SECRET_KEY == "":
                print("🚨 CRITICAL: Missing SECRET_KEY in production. Security functionality will fail.")

settings = Settings()