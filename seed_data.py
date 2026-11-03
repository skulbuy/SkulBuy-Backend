import uuid
from sqlalchemy.orm import Session
from database import engine, Base
import models
from services import utils

def run_seed(db: Session = None):
    close_after = False
    if db is None:
        from database import SessionLocal
        # Fallback if SessionLocal not exported:
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        close_after = True

    try:
        # Create all tables first
        Base.metadata.create_all(bind=engine)

        print(">> Seeding Categories...")
        categories_data = [
            {"name": "Laptops & Tech", "description": "Laptops, chargers, accessories, calculators, and electronics for coursework"},
            {"name": "Phones & Tablets", "description": "Smartphones, power banks, airpods, chargers, and phone accessories"},
            {"name": "Textbooks & Handouts", "description": "Engineering, Science, Agriculture, and general course textbooks and lecture handouts"},
            {"name": "Hostel & Living", "description": "Rechargeable fans, mattresses, hot plates, kettles, reading lamps"},
            {"name": "Fashion & Campus Wear", "description": "Hoodies, kicks, shirts, corporate wears for presentations, and campus fits"},
            {"name": "Sports & Fitness", "description": "Jerseys, boots, workout gear, and gym accessories"},
        ]

        cat_map = {}
        for cdata in categories_data:
            existing = db.query(models.Category).filter(models.Category.name == cdata["name"]).first()
            if not existing:
                cat = models.Category(
                    id=uuid.uuid4(),
                    name=cdata["name"],
                    description=cdata["description"]
                )
                db.add(cat)
                db.commit()
                db.refresh(cat)
                cat_map[cdata["name"]] = cat
                print(f"   + Created Category: {cat.name}")
            else:
                cat_map[cdata["name"]] = existing

        print(">> Seeding Pickup Hubs...")
        hubs_data = [
            {"name": "Bosso Campus Central Hub", "campus": "FUT Minna", "location": "Students Union Building (SUB), Bosso Campus"},
            {"name": "Gidan Kwano Library Hub", "campus": "FUT Minna", "location": "University Main Library Ground Floor, Gidan Kwano"},
            {"name": "SEET Complex Station", "campus": "FUT Minna", "location": "School of Engineering & Engineering Tech, Gidan Kwano"},
        ]
        for hdata in hubs_data:
            existing_hub = db.query(models.PickupHub).filter(models.PickupHub.name == hdata["name"]).first()
            if not existing_hub:
                hub = models.PickupHub(
                    id=uuid.uuid4(),
                    name=hdata["name"],
                    campus=hdata["campus"],
                    location=hdata["location"],
                    is_active=True
                )
                db.add(hub)
                db.commit()
                print(f"   + Created Pickup Hub: {hub.name}")

        print(">> Seeding Campus Starter Seller...")
        seller_email = "store@skulbuy.com"
        seller = db.query(models.User).filter(models.User.email == seller_email).first()
        if not seller:
            seller = models.User(
                id=uuid.uuid4(),
                email=seller_email,
                matric_no="2021/1/00001CS",
                phone="08012345678",
                password_hash=utils.hash_password("Password123!"),
                full_name="SkulBuy Official Student Hub",
                school_name="FUT Minna",
                role=models.UserRole.VENDOR,
                status=models.UserStatus.ACTIVE,
                is_verified=True,
            )
            db.add(seller)
            db.commit()
            db.refresh(seller)

            vendor_prof = models.VendorProfile(
                user_id=seller.id,
                store_name="SkulBuy Official Campus Store",
                store_description="Curated student tech, hostel essentials, and verified items for FUT Minna students.",
                verification_level=2
            )
            db.add(vendor_prof)
            db.commit()
            print(f"   + Created Seller: {seller.email} (Password: Password123!)")

        print(">> Seeding Starter Campus Listings...")
        products_data = [
            {
                "title": "HP EliteBook 840 G5 (Core i5 8th Gen, 16GB RAM, 256GB SSD)",
                "category": "Laptops & Tech",
                "description": "Clean laptop suitable for programming, AutoCAD, MATLAB, and general engineering courses. 16GB RAM, 256GB fast SSD, full HD IPS screen, backlit keyboard, great battery backup. Comes with original HP charger.",
                "condition": models.ProductCondition.USED,
                "price_kobo": 18500000, # 185,000 NGN
                "stock": 2,
                "location": "Gidan Kwano Hostels / Bosso",
                "image": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80"
            },
            {
                "title": "Lontor 16\" Rechargeable Standing Fan (With Solar Charging Port)",
                "category": "Hostel & Living",
                "description": "Essential for campus hostel life. Super quiet 3-speed blades, LED nightlight, USB phone charging port, and lasts up to 10 hours on low speed during power outages. Clean condition.",
                "condition": models.ProductCondition.LIKE_NEW,
                "price_kobo": 3400000, # 34,000 NGN
                "stock": 3,
                "location": "Bosso Campus Block B",
                "image": "https://images.unsplash.com/photo-1618941716939-553df3c6c278?w=800&auto=format&fit=crop&q=80"
            },
            {
                "title": "Calculus & Analytic Geometry (George B. Thomas - 12th Ed)",
                "category": "Textbooks & Handouts",
                "description": "Standard textbook for MTH 111, MTH 121, and engineering mathematics. Complete pages, no tears, contains highlighted formulas and past question notes.",
                "condition": models.ProductCondition.USED,
                "price_kobo": 550000, # 5,500 NGN
                "stock": 5,
                "location": "Main Library Steps, Gidan Kwano",
                "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80"
            },
            {
                "title": "Oraimo 27,000mAh PowerBank Traveler 3 Byte (Dual 20W PD Fast)",
                "category": "Phones & Tablets",
                "description": "Massive 27000mAh capacity to keep your devices charged all week. Type-C PD 20W fast charging and micro-USB input. 100% authentic with Oraimo scratch verification code intact.",
                "condition": models.ProductCondition.BRAND_NEW,
                "price_kobo": 1950000, # 19,500 NGN
                "stock": 4,
                "location": "Bosso Campus SUB",
                "image": "https://images.unsplash.com/photo-1609592806787-3d9c5d1112ce?w=800&auto=format&fit=crop&q=80"
            },
            {
                "title": "Stainless Steel Electric Cordless Kettle 2.2L (Auto Cut-off)",
                "category": "Hostel & Living",
                "description": "Fast-boil 1500W electric kettle for morning tea, coffee, and quick hostel noodles. Double-layer heat insulation with automatic dry-boil safety shutoff.",
                "condition": models.ProductCondition.BRAND_NEW,
                "price_kobo": 750000, # 7,500 NGN
                "stock": 6,
                "location": "Gidan Kwano Off-Campus Lodges",
                "image": "https://images.unsplash.com/photo-1594213114663-d94db9b17125?w=800&auto=format&fit=crop&q=80"
            },
            {
                "title": "Oversized Heavyweight Campus Hoodie (FUT Minna Black - Size L)",
                "category": "Fashion & Campus Wear",
                "description": "Premium 380gsm fleece cotton hoodie. Soft interior, kangaroo pocket, durable ribbed cuffs. Perfect for cold harmattan morning 8am lectures.",
                "condition": models.ProductCondition.BRAND_NEW,
                "price_kobo": 1400000, # 14,000 NGN
                "stock": 5,
                "location": "Gidan Kwano / Bosso",
                "image": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800&auto=format&fit=crop&q=80"
            }
        ]

        for pdata in products_data:
            existing_prod = db.query(models.Product).filter(models.Product.title == pdata["title"]).first()
            if not existing_prod and pdata["category"] in cat_map:
                category = cat_map[pdata["category"]]
                prod = models.Product(
                    id=uuid.uuid4(),
                    vendor_id=seller.id,
                    category_id=category.id,
                    title=pdata["title"],
                    description=pdata["description"],
                    condition=pdata["condition"],
                    price_kobo=pdata["price_kobo"],
                    stock=pdata["stock"],
                    status=models.ProductStatus.ACTIVE,
                    location=pdata["location"],
                    prep_time_minutes=20
                )
                db.add(prod)
                db.commit()
                db.refresh(prod)

                img = models.ProductImage(
                    id=uuid.uuid4(),
                    product_id=prod.id,
                    image_url=pdata["image"],
                    sort_order=0
                )
                db.add(img)
                db.commit()
                print(f"   + Created Product: {prod.title} (₦{pdata['price_kobo'] / 100:,.2f})")

        print(">> Database Seeding Complete!")
        return {"status": "success", "message": "Categories, hubs, and sample products seeded successfully."}

    except Exception as e:
        db.rollback()
        print(f">> Seeding error: {e}")
        raise e
    finally:
        if close_after:
            db.close()

if __name__ == "__main__":
    run_seed()
