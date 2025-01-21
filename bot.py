import logging
import os
import asyncio

import dp
import requests

from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram import types
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import Command
from dotenv import load_dotenv

from database import (
    get_subscribers,
    add_wallet,
    update_balance,
    delete_wallet,
    get_user_wallets,
    get_all_wallets,
    is_admin,
    add_admin,
    update_db_schema,
    add_subscriber,
)


# Завантажуємо змінні середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()
print(f"✅ Loaded TOKEN: {TOKEN}")

# Головне меню (оновлене)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Мої гаманці"), KeyboardButton(text="💰 Баланс")],
        [
            KeyboardButton(text="➕ Додати гаманець"),
        ],
        [
            KeyboardButton(text="📊 Загальний баланс"),
            KeyboardButton(text="⚡ Призначити адміністратора"),
        ],
        [KeyboardButton(text="🔔 Підписатися на сповіщення")],
    ],
    resize_keyboard=True,
)


# 📌 Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    from database import add_user  # Імпортуємо функцію

    await add_user(user_id)  # Додаємо користувача в базу

    if await is_admin(user_id):
        role = "адміністратор"
    else:
        role = "звичайний користувач"

    await message.answer(f"👋 Вітаю! Ви {role}. Виберіть дію:", reply_markup=main_menu)


# 📌 Отримання балансу TRX через API Trongrid
def get_trx_balance(address):
    """Отримує баланс TRX на гаманці через Trongrid API"""
    url = f"https://api.trongrid.io/v1/accounts/{address}"

    try:
        response = requests.get(url, timeout=5)  # ⏳ Додаємо тайм-аут 5 секунд
        response.raise_for_status()  # 🚀 Піднімаємо помилку, якщо статус-код HTTP > 400
        data = response.json()

        if "data" in data and len(data["data"]) > 0:
            balance = (
                data["data"][0].get("balance", 0) / 1_000_000
            )  # Конвертація з SUN у TRX
            return balance
        return 0

    except requests.Timeout:
        print("⏳ Тайм-аут запиту Trongrid API")
    except requests.ConnectionError:
        print("🚫 Помилка з'єднання з Trongrid API")
    except requests.RequestException as e:
        print(f"❌ Загальна помилка запиту Trongrid: {str(e)}")

    return 0  # Якщо помилка, повертаємо 0


# 📌 Перегляд балансу користувача
@dp.message(Command("balance"))
async def balance_handler(message: Message):
    """Перевіряє баланс усіх гаманців користувача та оновлює його в базі"""
    user_id = message.from_user.id
    wallets = await get_user_wallets(user_id)

    if not wallets:
        await message.answer("⚠️ У вас немає збережених гаманців.")
        return

    text = "📊 **Ваші гаманці та баланси:**\n"
    for name, address, last_balance in wallets:
        balance = get_trx_balance(address)  # Отримуємо актуальний баланс
        await update_balance(address, balance)  # 🔹 Оновлюємо баланс у БД
        text += f"🔹 {name}: `{address}` → {balance} TRX\n"

    await message.answer(text)



@dp.message(Command("add_wallet"))
async def add_wallet_handler(message: Message):
    """Обробляє команду /add_wallet: якщо аргументи є – додає гаманець, якщо ні – надсилає підказку"""
    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:  # Якщо команда викликана без параметрів
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Скопіювати команду", callback_data="copy_add_wallet")]
            ]
        )

        await message.answer(
            "✏ **Щоб додати гаманець, введіть команду у форматі:**\n"
            "`/add_wallet Назва Адреса`\n\n"
            "📌 **Натисніть кнопку нижче, щоб отримати команду для копіювання!**",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    # Якщо користувач ввів назву та адресу – додаємо гаманець
    user_id = message.from_user.id
    name, address = parts[1], parts[2]

    success = await add_wallet(user_id, name, address)

    if success:
        await message.answer(f"✅ Гаманець `{name}` (`{address}`) успішно додано!")
    else:
        await message.answer("⚠️ Гаманець з такою адресою вже існує.")

@dp.callback_query(lambda c: c.data == "copy_add_wallet")
async def copy_add_wallet_callback(callback_query):
    """Надсилає команду /add_wallet користувачу у чат"""
    await bot.send_message(
        callback_query.from_user.id,
        "/add_wallet Назва Адреса"
    )
    await bot.answer_callback_query(callback_query.id, text="✅ Команда надіслана у ваш чат!")


# 📌 Відображення списку гаманців + кнопки видалення
@dp.message(Command("wallets"))
async def wallets_handler(message: Message):
    """Відображає список гаманців тільки для цього користувача"""
    user_id = message.from_user.id
    wallets = await get_user_wallets(user_id)

    if not wallets:
        await message.answer("⚠️ У вас немає збережених гаманців.")
        return

    for name, address, last_balance in wallets:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗑 Видалити", callback_data=f"delete:{name}"
                    )
                ]
            ]
        )
        await message.answer(
            f"📌 {name}: `{address}` (Баланс: {last_balance} TRX)",
            reply_markup=keyboard,
        )

@dp.message(Command("delete_wallet"))
async def delete_wallet_prompt(message: Message):
    user_id = message.from_user.id
    wallets = await get_user_wallets(user_id)

    if not wallets:
        await message.answer("⚠️ У вас немає збережених гаманців.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"delete:{name}")]
            for name, _, _ in wallets
        ]
    )

    await message.answer("📌 **Оберіть гаманець для видалення:**", reply_markup=keyboard)

# 📌 Видалення гаманця
@dp.callback_query(lambda c: c.data.startswith("delete:"))
async def delete_wallet_callback(callback_query):
    """Обробка натискання кнопки видалення"""
    user_id = callback_query.from_user.id
    name = callback_query.data.split(":")[1]
    success = await delete_wallet(user_id, name)

    if success:
        await callback_query.message.edit_text(f"✅ Гаманець `{name}` видалено!")
    else:
        await callback_query.message.edit_text(
            f"⚠️ Гаманець `{name}` не знайдено або ви не маєте доступу."
        )


@dp.message(Command("subscribe"))
async def subscribe_handler(message: Message):
    """Додає користувача в список підписників"""
    user_id = message.from_user.id
    success = await add_subscriber(user_id)

    if success:
        await message.answer("✅ Ви підписані на сповіщення про поповнення!")
    else:
        await message.answer("⚠ Ви вже підписані.")


async def check_wallets():
    """Перевіряє баланси всіх гаманців та надсилає сповіщення підписникам"""
    wallets = await get_all_wallets()  # Отримуємо всі гаманці

    for name, address, last_balance in wallets:
        new_balance = get_trx_balance(address)  # Отримуємо актуальний баланс через API

        if new_balance > last_balance:  # Перевіряємо, чи був депозит
            diff = new_balance - last_balance
            message = f"📥 Поповнення!\n🔹 **{name}**\n📍 `{address}`\n💰 +{diff} TRX (новий баланс: {new_balance} TRX)"

            # Отримуємо список підписаних користувачів
            subscribers = await get_subscribers()
            for user_id in subscribers:
                try:
                    await bot.send_message(user_id, message)
                except Exception as e:
                    print(
                        f"⚠️ Не вдалося надіслати повідомлення користувачу {user_id}: {e}"
                    )

            # Оновлюємо баланс у базі
            await update_balance(address, new_balance)


@dp.message(Command("total_balance"))
async def total_balance_handler(message: Message):
    """Оновлює баланси та виводить всі гаманці"""
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    wallets = await get_all_wallets()  # Отримуємо всі гаманці
    total_balance = 0
    text = "📊 **Всі гаманці та їх баланси:**\n"

    for name, address, last_balance in wallets:
        balance = get_trx_balance(address)  # Отримуємо актуальний баланс
        await update_balance(address, balance)  # 🔹 Оновлюємо баланс у БД
        total_balance += balance
        text += f"🔹 {name}: `{address}` → {balance} TRX\n"

    text += f"\n💰 **Загальний баланс:** {total_balance} TRX"
    await message.answer(text)


@dp.message(Command("set_admin"))
async def set_admin_handler(message: Message):
    """Призначає іншого адміністратора"""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "❌ **Формат команди неправильний!**\n\n"
            "Щоб отримати `user_id` користувача:\n"
            "1️⃣ Перейдіть у [@userinfobot](https://t.me/userinfobot)\n"
            "2️⃣ Надішліть команду `/start`\n"
            "3️⃣ Скопіюйте `user_id` та введіть команду:\n"
            "`/set_admin user_id`",
            disable_web_page_preview=True,
        )
        return

    new_admin_id = int(parts[1])

    from database import is_user_exists
    if not await is_user_exists(new_admin_id):
        await message.answer(
            f"⚠️ Користувач `{new_admin_id}` не знайдений у базі. Переконайтесь, що він запустив бота."
        )
        return

    await add_admin(new_admin_id)
    await message.answer(f"✅ Користувач `{new_admin_id}` тепер є адміністратором!")

async def scheduled_checker():
    """Перевіряє баланси гаманців та надсилає сповіщення про поповнення кожні 5 хвилин"""
    while True:
        await check_wallets()
        await asyncio.sleep(300)  # Чекаємо 5 хвилин


dp.message(Command("subscribe"))


async def subscribe_handler(message: Message):
    """Додає користувача в список підписників"""
    user_id = message.from_user.id
    await add_subscriber(user_id)
    await message.answer("✅ Ви підписані на сповіщення про поповнення!")

@dp.message(F.text == "📋 Мої гаманці")
async def show_wallets(message: Message):
    await wallets_handler(message)

@dp.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    """Обробляє кнопку "Баланс" та викликає основний обробник"""
    print("🔍 Натиснуто кнопку: Баланс")
    await balance_handler(message)

@dp.message(F.text == "📊 Загальний баланс")
async def total_balance_button(message: Message):
    await total_balance_handler(message)

# 📌 Обробка кнопок головного меню
@dp.message(lambda message: message.text == "📋 Мої гаманці")
async def show_wallets(message: Message):
    print("🔍 Натиснуто кнопку: Мої гаманці")
    await wallets_handler(message)


@dp.message(lambda message: message.text == "📊 Загальний баланс")
async def total_balance_button(message: Message):
    await total_balance_handler(message)


@dp.message(F.text == "⚡ Призначити адміністратора")
async def set_admin_button(message: Message):
    """Надає інструкцію з отримання user_id та формату команди"""
    explanation = (
        "👤 **Як отримати `user_id` користувача:**\n"
        "1️⃣ Перейдіть у [@userinfobot](https://t.me/userinfobot)\n"
        "2️⃣ Надішліть команду `/start`\n"
        "3️⃣ Скопіюйте отриманий `user_id`\n\n"
        "✏ **Введіть команду у форматі:**\n"
        "`/set_admin user_id`"
    )

    await message.answer(explanation, disable_web_page_preview=True)


@dp.message(F.text == "➕ Додати гаманець")
async def add_wallet_button(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопіювати команду", callback_data="copy_add_wallet")]
        ]
    )

    await message.answer(
        "✏ **Щоб додати гаманець, введіть команду у форматі:**\n"
        "`/add_wallet Назва Адреса`\n\n"
        "📌 **Натисніть кнопку нижче, щоб отримати команду для копіювання!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "🔔 Підписатися на сповіщення")
async def subscribe_button_handler(message: Message):
    """Обробляє натискання кнопки '🔔 Підписатися на сповіщення'"""
    await subscribe_handler(message)

async def main():
    await update_db_schema()  # Додаємо колонку is_subscribed
    print("✅ База даних оновлена!")
    print("✅ Бот запущено")
    asyncio.create_task(scheduled_checker())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
