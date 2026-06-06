import asyncio
from sqlalchemy import text
from app.db.session import engine, Base
from app.models.models import Seller, Product, Order, InventorySnapshot, PricingSnapshot, TrafficMetric, LogisticsMetric, ProductEmbedding, InsightEmbedding

async def init_db():
    print("Initializing CommercePulse Database...")
    
    async with engine.begin() as conn:
        # 1. Enable pgvector extension
        print("Enabling pgvector extension...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("pgvector extension ready.")
        except Exception as e:
            print(f"Could not enable pgvector: {e}")
            print("Trying to proceed without it (might fail on embedding tables)...")

        # 2. Create tables
        print("Creating tables...")
        try:
            # We need to import all models so SQLAlchemy knows about them
            await conn.run_sync(Base.metadata.create_all)
            print("Tables created successfully.")
        except Exception as e:
            print(f"Failed to create tables: {e}")
            return

    print("\nDatabase initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_db())
