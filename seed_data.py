"""
Seed script - populates MySQL with realistic demo data so you can test the
full flow (dropdown-driven order creation, negotiation emails, etc.)
without hand-crafting any UUIDs.

Run from the project root (same place as .env):

    python seed_data.py

Creates ~20 customers and ~100 products across several categories (about
30% deliberately out of stock, so negotiation actually triggers when you
order one of them). One customer uses the real email set in .env as
TEST_CUSTOMER_EMAIL - order as that customer to receive actual negotiation
emails in your own inbox.

Safe to re-run - skips anything that already exists (matched by email/SKU).
"""

import asyncio
import os
import random

from dotenv import load_dotenv
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Customer, Product

load_dotenv()

TEST_CUSTOMER_EMAIL = os.getenv("TEST_CUSTOMER_EMAIL", "you@example.com")

CUSTOMER_NAMES = [
    "Ayesha Siddiqui", "Bilal Hassan", "Sana Malik", "Usman Tariq", "Hira Farooq",
    "Zainab Ahmed", "Fahad Iqbal", "Mehwish Raza", "Saad Khalid", "Nida Sheikh",
    "Omar Baig", "Rabia Yousuf", "Hamza Shah", "Iqra Noor", "Talha Riaz",
    "Amna Qureshi", "Danish Aslam", "Mariam Javed", "Kashif Butt", "Sidra Anwar",
]

CATEGORIES = {
    "electronics": [
        "Wireless Mouse", "Wireless Mouse Pro", "Mechanical Keyboard", "USB-C Hub",
        "Bluetooth Speaker", "Noise Cancelling Headphones", "Webcam HD", "Power Bank 10000mAh",
        "Laptop Stand", "Wireless Charger", "HDMI Cable", "Smart Watch", "Earbuds Pro",
        "Portable SSD 1TB", "Monitor Arm", "Ring Light", "Phone Tripod", "Action Camera",
    ],
    "home": [
        "Desk Lamp", "Desk Lamp XL", "Ceramic Mug Set", "Throw Blanket", "Scented Candle",
        "Wall Clock", "Storage Basket", "Picture Frame Set", "Cushion Cover", "Table Runner",
        "Plant Pot", "Air Freshener", "Door Mat", "Curtain Set", "Bedsheet Set",
    ],
    "kitchen": [
        "Non-Stick Pan", "Chef Knife Set", "Cutting Board", "Blender", "Electric Kettle",
        "Coffee Maker", "Food Storage Set", "Measuring Cups", "Spice Rack", "Dish Rack",
    ],
    "fashion": [
        "Leather Wallet", "Canvas Backpack", "Sunglasses", "Wrist Watch", "Baseball Cap",
        "Cotton T-Shirt", "Denim Jacket", "Sports Shoes", "Formal Shoes", "Tote Bag",
    ],
    "fitness": [
        "Yoga Mat", "Resistance Bands", "Dumbbell Set", "Skipping Rope", "Water Bottle 1L",
        "Gym Gloves", "Foam Roller", "Fitness Tracker", "Protein Shaker", "Exercise Ball",
    ],
    "stationery": [
        "Notebook A5", "Gel Pen Set", "Sticky Notes", "Desk Organizer", "Highlighter Set",
        "Whiteboard", "File Folder Set", "Stapler", "Sketchbook", "Calculator",
    ],
    "beauty": [
        "Face Wash", "Moisturizer", "Sunscreen SPF50", "Lip Balm Set", "Hair Serum",
        "Shampoo 400ml", "Conditioner 400ml", "Nail Polish Set", "Makeup Brush Set", "Face Mask Pack",
        "Perfume 50ml", "Hand Cream", "Body Lotion", "Hair Dryer", "Beard Trimmer",
    ],
    "toys": [
        "Building Blocks Set", "Remote Control Car", "Puzzle 500pc", "Board Game", "Plush Toy",
        "Art Supply Kit", "Kids Bicycle Helmet", "Water Gun", "Kite", "Yo-Yo",
        "Card Game Deck", "Building Blocks Deluxe",
    ],
}


async def get_or_create_customer(db, email, name, phone):
    result = await db.execute(select(Customer).where(Customer.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False
    customer = Customer(name=name, email=email, phone=phone, preferences={})
    db.add(customer)
    await db.flush()
    return customer, True


async def get_or_create_product(db, sku, name, stock_qty, price, category):
    result = await db.execute(select(Product).where(Product.sku == sku))
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False
    product = Product(sku=sku, name=name, stock_qty=stock_qty, price=price, category=category, tags=[category])
    db.add(product)
    await db.flush()
    return product, True


async def main():
    random.seed(42)  # reproducible across re-runs

    async with AsyncSessionLocal() as db:
        created_customers = 0
        test_customer, was_new = await get_or_create_customer(
            db, email=TEST_CUSTOMER_EMAIL, name="Test Customer (you)", phone="03000000000"
        )
        created_customers += was_new

        for i, name in enumerate(CUSTOMER_NAMES, start=1):
            email = f"{name.lower().replace(' ', '.')}@example.com"
            _, was_new = await get_or_create_customer(db, email=email, name=name, phone=f"0300{1000000 + i}")
            created_customers += was_new

        created_products = 0
        sku_counter = 1
        for category, names in CATEGORIES.items():
            for name in names:
                sku = f"SKU-{sku_counter:04d}"
                # ~30% chance a product is out of stock, to make negotiation
                # actually trigger when you order one.
                stock_qty = 0 if random.random() < 0.30 else random.randint(3, 60)
                price = round(random.uniform(500, 15000), 2)
                _, was_new = await get_or_create_product(db, sku, name, stock_qty, price, category)
                created_products += was_new
                sku_counter += 1

        await db.commit()

        total_customers = (await db.execute(select(Customer))).scalars().all()
        total_products = (await db.execute(select(Product))).scalars().all()
        out_of_stock_example = next((p for p in total_products if p.stock_qty == 0), None)
        in_stock_example = next((p for p in total_products if p.stock_qty > 0), None)

    print(f"\nSeed complete.")
    print(f"  Customers: {len(total_customers)} total ({created_customers} newly created)")
    print(f"  Products:  {len(total_products)} total ({created_products} newly created)")
    print(f"\n  Test customer (receives real emails): {TEST_CUSTOMER_EMAIL}")
    print(f"    -> ID: {test_customer.id}")
    if out_of_stock_example:
        print(f"\n  Example out-of-stock product (triggers negotiation): {out_of_stock_example.name}")
        print(f"    -> ID: {out_of_stock_example.id}")
    if in_stock_example:
        print(f"  Example in-stock product (straight to fulfillment): {in_stock_example.name}")
        print(f"    -> ID: {in_stock_example.id}")
    print(f"\nOpen the Streamlit Orders page - customers and products now load in the dropdowns.\n")


if __name__ == "__main__":
    asyncio.run(main())
