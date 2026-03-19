import asyncio
from app.core.db import engine
from sqlalchemy import text

async def test_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Database connection successful! Result: {result.scalar()}")
    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
