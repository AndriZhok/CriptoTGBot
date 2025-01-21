import aiosqlite


async def update_db_schema():
    """Перевіряє, чи існує колонка `last_balance`, перш ніж додавати її"""
    async with aiosqlite.connect("wallets.db") as db:
        cursor = await db.execute("PRAGMA table_info(wallets)")
        columns = [
            column[1] for column in await cursor.fetchall()
        ]  # Отримуємо список назв стовпців

        if "last_balance" not in columns:
            await db.execute(
                "ALTER TABLE wallets ADD COLUMN last_balance REAL DEFAULT 0"
            )
            await db.commit()
            print("✅ Колонка `last_balance` додана")
        else:
            print("⚠️ Колонка `last_balance` вже існує, оновлення не потрібно")
