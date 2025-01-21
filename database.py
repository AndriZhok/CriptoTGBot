import aiosqlite

DB_NAME = "wallets.db"


async def init_db():
    """Створює таблиці, якщо вони ще не існують"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_admin INTEGER DEFAULT 0,
            subscribed INTEGER DEFAULT 0
        )
        """
        )
        await db.execute(
            """
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE,
            last_balance REAL DEFAULT 0
        )
        """
        )
        await db.commit()


async def add_wallet(user_id: int, name: str, address: str):
    """Додає новий гаманець у базу даних для конкретного користувача"""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO wallets (user_id, name, address) VALUES (?, ?, ?)",
                (user_id, name, address),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # Якщо гаманець вже існує


async def get_user_wallets(user_id: int):
    """Повертає список гаманців для конкретного користувача"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT name, address, last_balance FROM wallets WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchall()


async def update_balance(address, new_balance):
    """Оновлює баланс у базі даних"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE wallets SET last_balance = ? WHERE address = ?",
            (new_balance, address),
        )
        await db.commit()


async def get_all_wallets():
    """Отримує список усіх гаманців із бази (для адмінів)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT name, address, last_balance FROM wallets")
        wallets = await cursor.fetchall()
        return wallets


async def update_db_schema():
    """Додає колонку last_balance, якщо її немає"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("ALTER TABLE wallets ADD COLUMN last_balance REAL DEFAULT 0")
        await db.commit()
        print("✅ Схема бази даних оновлена!")


async def delete_wallet(user_id: int, name: str):
    """Видаляє гаманець користувача за назвою"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "DELETE FROM wallets WHERE user_id = ? AND name = ?", (user_id, name)
        )
        await db.commit()
        return cursor.rowcount > 0  # Повертає True, якщо гаманець був видалений


async def is_admin(user_id: int):
    """Перевіряє, чи є користувач адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT is_admin FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result and result[0] == 1  # Повертає True, якщо is_admin == 1


async def add_admin(user_id: int):
    """Додає користувача в базу як адміністратора"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, is_admin) VALUES (?, 1)", (user_id,)
        )
        await db.commit()


async def add_user(user_id: int):
    """Додає нового користувача у базу, якщо він ще не існує"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def get_subscribers():
    """Повертає список усіх користувачів, які підписалися на сповіщення"""
    async with aiosqlite.connect("wallets.db") as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE is_subscribed = 1")
        subscribers = await cursor.fetchall()
        return [row[0] for row in subscribers]


async def update_db_schema():
    """Оновлює схему бази даних, додаючи відсутні колонки"""
    async with aiosqlite.connect("wallets.db") as db:
        # Отримуємо список колонок таблиці
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]

        # Додаємо колонку лише якщо її ще немає
        if "is_subscribed" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN is_subscribed INTEGER DEFAULT 0"
            )
            await db.commit()
            print("✅ Колонка is_subscribed успішно додана!")
        else:
            print("⚠️ Колонка is_subscribed вже існує.")


async def add_subscriber(user_id: int):
    """Додає підписника у базу (або оновлює статус)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_subscribed = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def get_subscribers():
    """Отримує всіх підписаних користувачів"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE is_subscribed = 1")
        return [row[0] for row in await cursor.fetchall()]


async def is_user_exists(user_id: int) -> bool:
    """Перевіряє, чи існує користувач у базі"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] > 0  # Якщо хоча б один запис знайдено, повертаємо True
