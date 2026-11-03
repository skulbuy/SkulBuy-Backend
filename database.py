from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/skullbuy_db",
        validation_alias=AliasChoices("DB_URL", "DATABASE_URL"),
    )
    ALGORITHM: str = "HS256"
    KEY: str = "super_secret_skullbuy_jwt_key_futminna_2026"
    EXPIRE: int = 60
    REFRESH_EXPIRE_DAYS: int = 30
    PAYSTACK_SECRET_KEY: str = "sk_test_placeholder"
    PAYSTACK_PUBLIC_KEY: str = "pk_test_placeholder"
    PAYSTACK_WEBHOOK_SECRET: str = "placeholder_webhook_secret"
    PLATFORM_FEE_PERCENTAGE: float = 2.5
    CAMPUS_NAME: str = "FUT Minna"
    PROTECTION_WINDOW_HOURS: int = 24
    CLOUDINARY_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

db_url = settings.DB_URL.strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Ensure proper PostgreSQL driver selection (handles psycopg v3, psycopg2, and URL overrides gracefully)
if "postgresql" in db_url:
    has_psycopg3 = False
    try:
        import psycopg  # noqa: F401
        has_psycopg3 = True
    except (ImportError, ModuleNotFoundError):
        pass

    has_psycopg2 = False
    try:
        import psycopg2  # noqa: F401
        has_psycopg2 = True
    except (ImportError, ModuleNotFoundError):
        pass

    if has_psycopg3:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql+psycopg2://") and not has_psycopg2:
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    elif has_psycopg2:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql+psycopg://"):
            db_url = db_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)

is_sqlite = db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {
    "pool_pre_ping": True,
    "connect_args": connect_args
}
if not is_sqlite:
    engine_kwargs.update({
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
