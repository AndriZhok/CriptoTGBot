import os
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DEFAULT_ADMIN_ID = int(os.getenv("DEFAULT_ADMIN_ID"))

DB_NAME = os.getenv("DB_NAME")


async def init_db():
    """Ініціалізує базу даних і створює необхідні таблиці"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, 
                name TEXT,
                is_approved INTEGER DEFAULT 0
            )
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                address TEXT UNIQUE,
                balance REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        await db.commit()
        print("✅ База даних ініціалізована!")


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
            return False


async def get_user_wallets(user_id: int):
    """Повертає список гаманців для конкретного користувача"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT name, address, last_balance FROM wallets WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchall()


async def update_balance(address, new_balance):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE wallets SET last_balance = ? WHERE address = ?",
            (new_balance, address),
        )
        await db.commit()
        print(f"✅ Баланс {new_balance} USDT оновлено в БД для {address}")


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


async def delete_wallet(user_id, address):
    """Видаляє гаманець користувача з бази даних"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "DELETE FROM wallets WHERE user_id = ? AND address = ?", (user_id, address)
        )
        await db.commit()
        rows_deleted = cursor.rowcount
        return rows_deleted > 0


async def is_admin(user_id: int):
    """Перевіряє, чи є користувач адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT is_admin FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result and result[0] == 1


async def add_admin(user_id: int, username: str = None):
    """Додає користувача в базу як адміністратора та зберігає username"""
    async with aiosqlite.connect(DB_NAME) as db:
        if username:
            await db.execute(
                "INSERT INTO users (user_id, username, is_admin) VALUES (?, ?, 1) ON CONFLICT(user_id) DO UPDATE SET is_admin = 1, username = COALESCE(username, ?)",
                (user_id, username, username),
            )
        else:
            await db.execute(
                "UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,)
            )
        await db.commit()


async def add_user(user_id: int):
    """Додає нового користувача у базу, якщо він ще не існує"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def get_subscribers():
    """Повертає список усіх користувачів, які підписалися на сповіщення"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE is_subscribed = 1")
        subscribers = await cursor.fetchall()
        return [row[0] for row in subscribers]


async def update_db_schema():
    """Оновлює схему бази даних, додаючи відсутні колонки"""
    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]

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
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] > 0


async def is_user_approved(user_id):
    """Перевіряє, чи схвалений користувач адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT is_approved FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row and row[0] == 1


async def approve_user(user_id: int):
    """Адмін схвалює користувача"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_approved = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def add_user(user_id: int, username: str):
    """Додає нового користувача в базу, якщо його ще немає"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, is_approved) VALUES (?, ?, 0)",
            (user_id, username),
        )
        await db.commit()


async def get_pending_users():
    """Отримує всіх користувачів, які ще не схвалені"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id, username FROM users WHERE is_approved = 0"
        )
        return await cursor.fetchall()


async def remove_user(user_id):
    """Видаляє користувача з бази даних"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


async def remove_subscriber(user_id: int):
    """Змінює статус підписки користувача на 0 (відписка)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_subscribed = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def is_user_subscribed(user_id: int) -> bool:
    """Перевіряє, чи підписаний користувач"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT is_subscribed FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row and row[0] == 1


async def ensure_default_admin():
    """Гарантує, що визначений користувач завжди буде адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO users (user_id, is_admin) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET is_admin = 1;",
            (DEFAULT_ADMIN_ID, 1),
        )
        await db.commit()


async def get_wallets(user_id, is_admin):
    async with aiosqlite.connect(DB_NAME) as db:
        if is_admin:
            query = "SELECT name, address FROM wallets;"
            params = ()
        else:
            query = "SELECT name, address FROM wallets WHERE user_id = ?;"
            params = (user_id,)

        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()
