import aiosqlite

DB_NAME = "wallets.db"
DATABASE_PATH = "wallets.db"

async def init_db():
    """Створює таблиці, якщо вони ще не існують"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_admin INTEGER DEFAULT 0,
            subscribed INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0
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
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE wallets SET last_balance = ? WHERE address = ?", (new_balance, address)
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
    async with aiosqlite.connect("wallets.db") as db:
        cursor = await db.execute(
            "DELETE FROM wallets WHERE user_id = ? AND address = ?", (user_id, address)
        )
        await db.commit()
        rows_deleted = cursor.rowcount
        return rows_deleted > 0  # True, якщо щось видалено, False, якщо ні


async def is_admin(user_id: int):
    """Перевіряє, чи є користувач адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT is_admin FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result and result[0] == 1  # Повертає True, якщо is_admin == 1


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


async def is_user_approved(user_id):
    """Перевіряє, чи схвалений користувач адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT is_approved FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row and row[0] == 1  # Повертає True, якщо is_approved = 1


async def approve_user(user_id: int):
    """Адмін схвалює користувача"""
    async with aiosqlite.connect("wallets.db") as db:
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
        return row and row[0] == 1  # True, якщо користувач підписаний


async def ensure_default_admin():
    """Гарантує, що користувач 6670900795 завжди буде адміністратором"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO users (user_id, is_admin) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET is_admin = 1;",
            (6670900795, 1),
        )
        await db.commit()
