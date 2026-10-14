from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str = "postgresql://postgres:postgres@localhost:5432/skullbuy_db"
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

is_sqlite = settings.DB_URL.startswith("sqlite")
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

engine = create_engine(settings.DB_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
