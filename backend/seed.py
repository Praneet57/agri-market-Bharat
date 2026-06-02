import asyncio
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.product import Product

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        r = await db.execute(select(User).where(User.phone=="9000000001"))
        if r.scalar_one_or_none():
            print("✅ Already seeded."); return
        farmer = User(full_name="Ravi Kumar",phone="9000000001",email="ravi@farm.com",
                      hashed_password=get_password_hash("farmer123"),role="farmer",
                      village="Palani",district="Dindigul",state="Tamil Nadu",latitude=10.4533,longitude=77.5194)
        buyer = User(full_name="Priya Traders",phone="9000000002",email="priya@traders.com",
                     hashed_password=get_password_hash("buyer123"),role="buyer",
                     district="Coimbatore",state="Tamil Nadu",latitude=11.0168,longitude=76.9558)
        db.add(farmer); db.add(buyer); await db.flush()
        for p in [
            Product(farmer_id=farmer.id,name="Alphonso Mangoes",category="Fruits",quantity_kg=500,price_per_kg=120,min_order_kg=50,district="Dindigul",latitude=10.4533,longitude=77.5194,is_organic=True,description="Premium quality sweet mangoes"),
            Product(farmer_id=farmer.id,name="Fresh Tomatoes",category="Vegetables",quantity_kg=1000,price_per_kg=18,min_order_kg=100,district="Dindigul",latitude=10.4533,longitude=77.5194),
            Product(farmer_id=farmer.id,name="Red Onions",category="Vegetables",quantity_kg=2000,price_per_kg=22,min_order_kg=200,district="Dindigul",latitude=10.4533,longitude=77.5194),
            Product(farmer_id=farmer.id,name="Turmeric",category="Spices",quantity_kg=200,price_per_kg=85,min_order_kg=20,district="Dindigul",latitude=10.4533,longitude=77.5194,is_organic=True),
        ]: db.add(p)
        await db.commit()
        print("✅ Seeded!\n   Farmer: 9000000001 / farmer123\n   Buyer:  9000000002 / buyer123")

asyncio.run(seed())
