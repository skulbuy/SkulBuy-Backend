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

        print(">> Seeding Campus Communities...")
        communities_data = [
            {
                "name": "FUT Minna General Marketplace Hub",
                "slug": "futminna-general-hub",
                "description": "Official campus community for verified FUT Minna students across Bosso and Gidan Kwano.",
                "category": "campus_life",
                "university": "FUT Minna",
                "icon": "🎓",
                "banner_color": "from-amber-600 to-orange-600",
                "is_official": True,
            },
            {
                "name": "SEET & SICT Tech & Gadgets Exchange",
                "slug": "futminna-tech-exchange",
                "description": "Buy, sell, and swap laptops, Arduino kits, calculators, and programming gear.",
                "category": "tech",
                "university": "FUT Minna",
                "icon": "💻",
                "banner_color": "from-blue-600 to-indigo-700",
                "is_official": True,
            },
            {
                "name": "Gidan Kwano & Bosso Hostel Deals",
                "slug": "futminna-hostel-deals",
                "description": "Roommate finder, mattresses, rechargeable fans, gas cylinders, and lodge clearances.",
                "category": "housing",
                "university": "FUT Minna",
                "icon": "🏠",
                "banner_color": "from-emerald-600 to-teal-700",
                "is_official": False,
            },
            {
                "name": "100L - 500L Textbooks & Past Questions",
                "slug": "futminna-academics",
                "description": "MTH, PHY, CHM, GST textbooks, lab coats, drawing boards, and exam study groups.",
                "category": "academics",
                "university": "FUT Minna",
                "icon": "📚",
                "banner_color": "from-purple-600 to-violet-700",
                "is_official": False,
            },
        ]

        for cdata in communities_data:
            existing_comm = db.query(models.Community).filter(models.Community.slug == cdata["slug"]).first()
            if not existing_comm:
                comm = models.Community(
                    id=uuid.uuid4(),
                    name=cdata["name"],
                    slug=cdata["slug"],
                    description=cdata["description"],
                    category=cdata["category"],
                    university=cdata["university"],
                    icon=cdata["icon"],
                    banner_color=cdata["banner_color"],
                    is_official=cdata["is_official"],
                    created_by=seller.id,
                )
                db.add(comm)
                db.flush()
                db.add(models.CommunityMember(community_id=comm.id, user_id=seller.id, role="admin"))
                welcome_msg = models.CommunityMessage(
                    community_id=comm.id,
                    user_id=seller.id,
                    content=f"Welcome to {comm.name}! Remember to always use SkulBuy Escrow & your 4-Digit Handover PIN when trading on campus.",
                    message_type="announcement",
                    is_pinned=True,
                )
                db.add(welcome_msg)
                db.commit()

        print(">> Seeding Campus Meetups...")
        meetups_data = [
            {
                "title": "FUT Minna Campus Tech & Creators Swap Meet",
                "description": "Bring your laptops, gadgets, and accessories for live inspection, diagnostics, and instant Escrow trades at Gidan Kwano.",
                "category": "tech",
                "university": "FUT Minna",
                "campus": "Gidan Kwano Campus",
                "location_name": "SICT Lecture Theatre Foyer, Gidan Kwano",
                "event_date": "2026-11-21",
                "event_time": "14:00",
                "max_attendees": 120,
                "is_featured": True,
                "banner_image": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80",
            },
            {
                "title": "Final Year Clearance & Hostel Yard Sale",
                "description": "Graduating 500L students clearing out standing fans, mattresses, gas cylinders, and textbooks at student-friendly prices.",
                "category": "trade_fair",
                "university": "FUT Minna",
                "campus": "Bosso Campus",
                "location_name": "Bosso Campus SUB Car Park",
                "event_date": "2026-11-28",
                "event_time": "11:00",
                "max_attendees": 200,
                "is_featured": True,
                "banner_image": "https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800&auto=format&fit=crop&q=80",
            },
        ]

        for mdata in meetups_data:
            existing_meetup = db.query(models.Meetup).filter(models.Meetup.title == mdata["title"]).first()
            if not existing_meetup:
                m = models.Meetup(
                    id=uuid.uuid4(),
                    title=mdata["title"],
                    description=mdata["description"],
                    category=mdata["category"],
                    university=mdata["university"],
                    campus=mdata["campus"],
                    location_name=mdata["location_name"],
                    event_date=mdata["event_date"],
                    event_time=mdata["event_time"],
                    organizer_id=seller.id,
                    max_attendees=mdata["max_attendees"],
                    is_featured=mdata["is_featured"],
                    banner_image=mdata["banner_image"],
                )
                db.add(m)
                db.flush()
                db.add(models.MeetupAttendee(meetup_id=m.id, user_id=seller.id, status="going"))
                db.commit()

        print(">> Seeding SkulBox Cycle...")
        existing_cycle = db.query(models.SkulBoxCycle).first()
        if not existing_cycle:
            cycle = models.SkulBoxCycle(
                id=uuid.uuid4(),
                title="Harmattan Semester Food & Provisions Bulk Cycle",
                season_tag="Harmattan 2026 Batch",
                university="FUT Minna",
                start_date="2026-11-01",
                lock_date="2026-11-30",
                delivery_date="2026-12-05",
                pickup_location="Gidan Kwano SUB & Bosso Central Hub",
                status="open",
                discount_pct=25,
                max_slots=250,
            )
            db.add(cycle)
            db.commit()

        print(">> Database Seeding Complete!")
        return {"status": "success", "message": "Categories, hubs, sample products, communities, meetups, and SkulBox cycles seeded successfully."}

    except Exception as e:
        db.rollback()
        print(f">> Seeding error: {e}")
        raise e
    finally:
        if close_after:
            db.close()

if __name__ == "__main__":
    run_seed()

