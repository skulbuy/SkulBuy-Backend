from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, Base, get_db
import models

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 Routers
API_V1_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(vendors.router, prefix=API_V1_PREFIX)
app.include_router(categories.router, prefix=API_V1_PREFIX)
app.include_router(products.router, prefix=API_V1_PREFIX)
app.include_router(pickup_hubs.router, prefix=API_V1_PREFIX)
app.include_router(orders.router, prefix=API_V1_PREFIX)
app.include_router(payments.router, prefix=API_V1_PREFIX)
app.include_router(delivery.router, prefix=API_V1_PREFIX)
app.include_router(disputes.router, prefix=API_V1_PREFIX)
app.include_router(reviews.router, prefix=API_V1_PREFIX)
app.include_router(admin.router, prefix=API_V1_PREFIX)

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
