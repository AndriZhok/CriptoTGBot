import asyncio
from database import init_db


async def main():
    await init_db()
    print("✅ База даних створена!")


if __name__ == "__main__":
    asyncio.run(main())
