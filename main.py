from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, Base, get_db
import models
import schemas
from routers.products import list_products, get_product, create_product, update_product, delete_product

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
)
import seed_data

# Initialize Database Tables (Gracefully attempts connection)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f">> Notice: Database auto-creation deferred or waiting for connection: {e}")


tags_metadata = [
    {"name": "Authentication", "description": "Student signup, login, matric verification, and session token rotation."},
    {"name": "Users", "description": "User profiles and delivery addresses."},
    {"name": "Vendors", "description": "Vendor store onboarding, settings, and payout bank configuration."},
    {"name": "Categories", "description": "Marketplace category and subcategory hierarchy."},
    {"name": "Products & Marketplace", "description": "Browse, search, filter, and vendor product listing management."},
    {"name": "Pickup Hubs", "description": "FUT Minna campus pickup stations (Method A fulfilment)."},
    {"name": "Orders & State Machine", "description": "Order placement, vendor SLA handling, and strict state transitions."},
    {"name": "Payments & Protected Checkout", "description": "Paystack Protected Checkout initialization and idempotent HMAC webhooks."},
    {"name": "Delivery & Hub OTP Verification", "description": "Buyer delivery OTP retrieval and Pickup Hub handover verification."},
    {"name": "Disputes", "description": "Buyer dispute filing, order freezing, and manual admin resolution."},
    {"name": "Reviews & Ratings", "description": "Post-delivery reviews and rating metrics."},
    {"name": "Admin & Ops Queue", "description": "Operational queues: pending vendors, dispute reviews, audit logs, and batch settlement."},
    {"name": "System", "description": "Health checks and connectivity diagnostics."},
]

app = FastAPI(
    title="SkulBuy Backend API — FUT Minna Launch",
    description="Campus P2P marketplace backend with Protected Checkout, Campus Hub delivery, and strict state machine.",
    version="2.0.0",
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
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

listings_router = APIRouter(prefix="/listings", tags=["Listings"])
listings_router.add_api_route("", list_products, methods=["GET"], response_model=list[schemas.ProductOut])
listings_router.add_api_route("/{product_id}", get_product, methods=["GET"], response_model=schemas.ProductOut)
listings_router.add_api_route("", create_product, methods=["POST"], response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
listings_router.add_api_route("/{product_id}", update_product, methods=["PATCH"], response_model=schemas.ProductOut)
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

@app.post("/api/seed", tags=["System"])
@app.post("/api/v1/seed", tags=["System"])
@app.get("/api/seed", tags=["System"])
@app.get("/api/v1/seed", tags=["System"])
def seed_database_endpoint(db: Session = Depends(get_db)):
    """Seeds the database with categories, pickup hubs, and initial student listings."""
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
            "version": "2.0.0"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

@app.on_event("startup")
def print_routes():
    print("\n" + "=" * 60)
    print("  SKULBUY MVP v2 API ROUTES")
    print("=" * 60)
    found_any = False
    for route in app.routes:
        if isinstance(route, APIRoute):
            found_any = True
            print(f"[{','.join(route.methods)}] {route.path}")

    if not found_any:
        print(">> No routes registered.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
