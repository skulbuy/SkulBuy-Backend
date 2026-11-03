import os
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, Base, get_db
import models
import schemas
from routers.products import (
    list_products,
    get_product,
    create_product,
    update_product,
    update_product_status,
    delete_product,
)

# Routers
from routers import (
    auth,
    users,
    vendors,
    categories,
    products,
    pickup_hubs,
    orders,
    payments,
    delivery,
    disputes,
    reviews,
    admin,
    campus_features,
)
import seed_data


def run_safe_migrations():
    """Safely adds new columns and enum values to existing PostgreSQL tables without data loss."""
    enum_statements = [
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SELLER'",
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'AMBASSADOR'",
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'seller'",
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ambassador'",
        "ALTER TYPE productcondition ADD VALUE IF NOT EXISTS 'BRAND_NEW'",
        "ALTER TYPE productcondition ADD VALUE IF NOT EXISTS 'brand_new'",
        "ALTER TYPE productstatus ADD VALUE IF NOT EXISTS 'WITHDRAWN'",
        "ALTER TYPE productstatus ADD VALUE IF NOT EXISTS 'SUSPENDED'",
        "ALTER TYPE productstatus ADD VALUE IF NOT EXISTS 'withdrawn'",
        "ALTER TYPE productstatus ADD VALUE IF NOT EXISTS 'suspended'",
        "ALTER TYPE deliverymethod ADD VALUE IF NOT EXISTS 'DOORSTEP_DELIVERY'",
        "ALTER TYPE deliverymethod ADD VALUE IF NOT EXISTS 'doorstep_delivery'",
        "ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'PAID'",
        "ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'paid'",
    ]
    alter_statements = [
        # Users table columns
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(150)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS level_of_study VARCHAR(50)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS campus_area VARCHAR(150)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS student_id_verified INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS id_card_image TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 100",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_balance_kobo BIGINT DEFAULT 100000",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_streak INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS longest_streak INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reward_date VARCHAR(20)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_bonus_claimed BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_onboarded BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
        # Products table columns
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS university VARCHAR(150) DEFAULT 'FUT Minna'",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_negotiable BOOLEAN DEFAULT TRUE",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_boosted BOOLEAN DEFAULT FALSE",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_rental BOOLEAN DEFAULT FALSE",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS rental_period VARCHAR(50)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS views INTEGER DEFAULT 0",
    ]
    for stmt in enum_statements:
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(stmt))
        except Exception as e:
            print(f">> Enum migration notice for '{stmt}': {e}")

    for stmt in alter_statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception as e:
            print(f">> Column migration notice for '{stmt}': {e}")


# Initialize Database Tables & Safe Migrations
try:
    Base.metadata.create_all(bind=engine)
    run_safe_migrations()
except Exception as e:
    print(f">> Notice: Database auto-creation deferred or waiting for connection: {e}")


tags_metadata = [
    {"name": "Authentication", "description": "Student signup, login, email OTP verification, and session token rotation."},
    {"name": "Users", "description": "User profiles, ID card verification, and delivery addresses."},
    {"name": "Vendors", "description": "Vendor store onboarding, settings, and payout bank configuration."},
    {"name": "Categories", "description": "Marketplace category and subcategory hierarchy."},
    {"name": "Products & Marketplace", "description": "Browse, search, filter, and vendor product listing management."},
    {"name": "Pickup Hubs", "description": "FUT Minna campus pickup stations (Method A fulfilment)."},
    {"name": "Orders & State Machine", "description": "Order placement, vendor SLA handling, and strict state transitions."},
    {"name": "Payments & Protected Checkout", "description": "Paystack Protected Checkout initialization and idempotent HMAC webhooks."},
    {"name": "Delivery & Hub OTP Verification", "description": "Buyer delivery OTP retrieval and Pickup Hub handover verification."},
    {"name": "Disputes", "description": "Buyer dispute filing, order freezing, and manual admin resolution."},
    {"name": "Reviews & Ratings", "description": "Post-delivery reviews and rating metrics."},
    {"name": "Campus Ecosystem & Features", "description": "Wallet, Daily Streak Rewards, Communities, Direct Chats, Meetups, SkulBox, and Skully AI."},
    {"name": "Admin & Ops Queue", "description": "Operational queues: pending vendors, dispute reviews, audit logs, and batch settlement."},
    {"name": "System", "description": "Health checks and connectivity diagnostics."},
]

app = FastAPI(
    title="SkulBuy Backend API — Full Campus Ecosystem",
    description="Campus P2P marketplace backend with Protected Checkout, Wallet, Communities, Direct Chat, Meetups, SkulBox, and Skully AI.",
    version="2.1.0",
    openapi_tags=tags_metadata,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://skulbuy-backend-f36c6.containers.snapdeploy.app",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files statically
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

listings_router = APIRouter(prefix="/listings", tags=["Listings"])
listings_router.add_api_route("", list_products, methods=["GET"], response_model=list[schemas.ProductOut])
listings_router.add_api_route("/{product_id}", get_product, methods=["GET"], response_model=schemas.ProductOut)
listings_router.add_api_route("", create_product, methods=["POST"], response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
listings_router.add_api_route("/{product_id}", update_product, methods=["PATCH"], response_model=schemas.ProductOut)
listings_router.add_api_route("/{product_id}/status", update_product_status, methods=["PATCH"], response_model=schemas.ProductOut)
listings_router.add_api_route("/{product_id}", delete_product, methods=["DELETE"], status_code=status.HTTP_204_NO_CONTENT)

# Mount API Routers (supporting both /api and /api/v1 for seamless frontend compatibility)
for prefix in ["/api/v1", "/api"]:
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(vendors.router, prefix=prefix)
    app.include_router(categories.router, prefix=prefix)
    app.include_router(products.router, prefix=prefix)
    app.include_router(listings_router, prefix=prefix)
    app.include_router(pickup_hubs.router, prefix=prefix)
    app.include_router(orders.router, prefix=prefix)
    app.include_router(payments.router, prefix=prefix)
    app.include_router(delivery.router, prefix=prefix)
    app.include_router(disputes.router, prefix=prefix)
    app.include_router(reviews.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(campus_features.router, prefix=prefix)


@app.post("/api/seed", tags=["System"])
@app.post("/api/v1/seed", tags=["System"])
@app.get("/api/seed", tags=["System"])
@app.get("/api/v1/seed", tags=["System"])
def seed_database_endpoint(db: Session = Depends(get_db)):
    """Seeds the database with categories, pickup hubs, initial student listings, communities, meetups, and SkulBox cycles."""
    return seed_data.run_seed(db)


@app.get("/health", tags=["System"])
async def health_check(db: Session = Depends(get_db)):
    """
    Lightweight health check verifying database connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "active",
            "backend": "online",
            "database": "connected",
            "campus": "FUT Minna",
            "version": "2.1.0",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )


@app.on_event("startup")
def on_startup():
    try:
        seed_data.run_seed()
    except Exception as e:
        print(f">> Startup seed notice: {e}")

    print("\n" + "=" * 60)
    print("  SKULBUY FULL CAMPUS ECOSYSTEM API ROUTES (v2.1.0)")
    print("=" * 60)
    for route in app.routes:
        if isinstance(route, APIRoute):
            print(f"[{','.join(route.methods)}] {route.path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
