import aiosqlite

async def update_db_schema():
    """Перевіряє, чи існують необхідні колонки та додає їх, якщо вони відсутні"""
    async with aiosqlite.connect("wallets.db") as db:
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in await cursor.fetchall()]

        # Додаємо колонку `is_approved`, якщо її немає
        if "is_approved" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 0")
            await db.commit()
            print("✅ Колонка `is_approved` додана")

        else:
            print("⚠️ Колонка `is_approved` вже існує, оновлення не потрібно")