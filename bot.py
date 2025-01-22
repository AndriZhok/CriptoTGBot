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
    is_user_approved,
    approve_user,
    remove_subscriber,
    is_user_subscribed, ensure_default_admin,
)


# Завантажуємо змінні середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Головне меню (оновлене)
async def get_main_menu(user_id):
    """Формує головне меню відповідно до ролі користувача"""
    is_subscribed = await is_user_subscribed(user_id)
    if await is_admin(user_id):
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📋 Мої гаманці"),
                    KeyboardButton(text="💰 Баланс"),
                ],
                [KeyboardButton(text="➕ Додати гаманець")],
                [
                    KeyboardButton(text="📊 Загальний баланс"),
                    KeyboardButton(text="⚡ Призначити адміністратора"),
                ],
                [
                    KeyboardButton(text="👥 Схвалити користувачів")
                ],  # 🔹 Нова кнопка для адмінів
                [
                    (
                        KeyboardButton(text="🔕 Відписатися")
                        if is_subscribed
                        else KeyboardButton(text="🔔 Підписатися на сповіщення")
                    )
                ],
            ],
            resize_keyboard=True,
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    (
                        KeyboardButton(text="🔕 Відписатися")
                        if is_subscribed
                        else KeyboardButton(text="🔔 Підписатися на сповіщення")
                    )
                ],
            ],
            resize_keyboard=True,
        )


@dp.message(F.text == "👥 Схвалити користувачів")
async def approve_users_button_handler(message: Message):
    """Адмін натискає кнопку "Схвалити користувачів" для перегляду запитів"""
    await pending_users_handler(message)


async def check_access(message: Message):
    """Перевіряє, чи користувач має доступ до бота"""
    user_id = message.from_user.id
    if not await is_user_approved(user_id):
        await message.answer(
            "❌ У вас немає доступу до бота. Дочекайтеся схвалення адміністратора."
        )
        return False
    return True


def get_trx_to_usdt_rate():
    """Отримує поточний курс TRX до USDT через API Binance"""
    url = "https://api.binance.com/api/v3/ticker/price?symbol=TRXUSDT"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data["price"])  # Отримуємо курс TRX/USDT
    except requests.RequestException as e:
        print(f"❌ Помилка отримання курсу TRX/USDT: {e}")
        return 0


# 📌 Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    """Обробляє команду /start з перевіркою доступу користувача"""
    user_id = message.from_user.id
    username = (
        message.from_user.username or f"user_{user_id}"
    )  # Якщо username відсутній

    from database import add_user

    await add_user(user_id, username)  # Додаємо користувача в базу з username

    if not await is_user_approved(user_id):
        await message.answer(
            "❌ Доступ до бота заборонено. Дочекайтеся схвалення адміністратора."
        )
        return

    role = "адміністратор" if await is_admin(user_id) else "звичайний користувач"
    menu = await get_main_menu(user_id)  # Визначаємо меню відповідно до ролі

    await message.answer(f"👋 Вітаю! Ви {role}. Виберіть дію:", reply_markup=menu)


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
    if not await check_access(message):
        return

    """Перевіряє баланс усіх гаманців користувача та оновлює його в базі"""
    user_id = message.from_user.id
    wallets = await get_user_wallets(user_id)

    if not wallets:
        await message.answer("⚠️ У вас немає збережених гаманців.")
        return

    trx_to_usdt = get_trx_to_usdt_rate()  # Отримуємо курс TRX/USDT
    if trx_to_usdt == 0:
        await message.answer("⚠️ Не вдалося отримати курс TRX/USDT. Спробуйте пізніше.")
        return

    text = "📊 **Ваші гаманці та баланси:**\n"
    total_trx = 0

    for name, address, last_balance in wallets:
        balance = get_trx_balance(address)  # Отримуємо актуальний баланс TRX
        await update_balance(address, balance)  # 🔹 Оновлюємо баланс у БД
        balance_usdt = balance * trx_to_usdt  # Конвертуємо TRX → USDT
        total_trx += balance

        text += (
            f"🔹 {name}: `{address}`\n"
            f"💰 {balance:.2f} TRX ≈ {balance_usdt:.2f} USDT\n\n"
        )

    total_usdt = total_trx * trx_to_usdt
    text += f"\n💰 **Загальний баланс:** {total_trx:.2f} TRX ≈ {total_usdt:.2f} USDT"

    await message.answer(text)


@dp.message(Command("add_wallet"))
async def add_wallet_handler(message: Message):
    """Обробляє команду /add_wallet: (Доступ тільки для адмінів)"""
    user_id = message.from_user.id

    # 🔒 Доступ тільки для адміністраторів
    if not await is_admin(user_id):
        await message.answer("❌ Ви не маєте прав додавати гаманці.")
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:  # Якщо команда викликана без параметрів
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Скопіювати команду", callback_data="copy_add_wallet"
                    )
                ]
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
    name, address = parts[1], parts[2]

    success = await add_wallet(user_id, name, address)

    if success:
        await message.answer(f"✅ Гаманець `{name}` (`{address}`) успішно додано!")
    else:
        await message.answer("⚠️ Гаманець з такою адресою вже існує.")


@dp.callback_query(lambda c: c.data == "copy_add_wallet")
async def copy_add_wallet_callback(callback_query):
    """Надсилає команду /add_wallet користувачу у чат"""
    await bot.send_message(callback_query.from_user.id, "/add_wallet Назва Адреса")
    await bot.answer_callback_query(
        callback_query.id, text="✅ Команда надіслана у ваш чат!"
    )


# 📌 Відображення списку гаманців + кнопки видалення
@dp.message(Command("wallets"))
async def wallets_handler(message: Message):
    """Відображає список гаманців користувача з балансом у TRX та USDT з можливістю видалення"""
    if not await check_access(message):
        return

    user_id = message.from_user.id
    wallets = await get_user_wallets(user_id)

    if not wallets:
        await message.answer("⚠️ У вас немає збережених гаманців.")
        return

    trx_to_usdt = get_trx_to_usdt_rate()  # Отримуємо актуальний курс TRX/USDT
    if trx_to_usdt == 0:
        await message.answer("⚠️ Не вдалося отримати курс TRX/USDT. Спробуйте пізніше.")
        return

    for name, address, last_balance in wallets:
        balance = get_trx_balance(address)  # Отримуємо актуальний баланс TRX
        await update_balance(address, balance)  # Оновлюємо баланс у БД
        balance_usdt = balance * trx_to_usdt  # Конвертуємо TRX → USDT

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗑 Видалити", callback_data=f"delete_wallet:{address}"
                    )
                ]
            ]
        )

        await message.answer(
            f"📌 **{name}**\n"
            f"📍 `{address}`\n"
            f"💰 {balance:.2f} TRX ≈ {balance_usdt:.2f} USDT",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


@dp.callback_query(lambda c: c.data.startswith("delete_wallet:"))
async def delete_wallet_callback(callback_query: types.CallbackQuery):
    """Обробник кнопки видалення гаманця"""
    user_id = callback_query.from_user.id
    address = callback_query.data.split(":")[1]

    success = await delete_wallet(user_id, address)

    if success:
        await callback_query.message.edit_text(f"✅ Гаманець `{address}` видалено!")
    else:
        await callback_query.message.answer(
            "⚠️ Помилка видалення гаманця. Можливо, він вже був видалений."
        )

    await callback_query.answer()  # Закриваємо сповіщення


@dp.message(Command("subscribe"))
async def subscribe_handler(message: Message):
    """Додає користувача в список підписників"""
    if not await check_access(message):
        return

    user_id = message.from_user.id
    success = await add_subscriber(user_id)

    if success:
        await message.answer("✅ Ви підписані на сповіщення про поповнення!")

        # Оновлення меню після підписки
        menu = await get_main_menu(user_id)
        await message.answer("Оновлено меню:", reply_markup=menu)
    else:
        await message.answer("⚠ Ви вже підписані.")


async def check_wallets():
    """Перевіряє баланси всіх гаманців та надсилає сповіщення підписникам"""
    wallets = await get_all_wallets()  # Отримуємо всі гаманці
    trx_to_usdt = get_trx_to_usdt_rate()  # Отримуємо курс TRX → USDT

    logging.info(f"🔄 Початок перевірки балансів, знайдено {len(wallets)} гаманців")

    for name, address, last_balance in wallets:
        new_balance = get_trx_balance(address)  # Отримуємо актуальний баланс через API
        logging.info(
            f"🔍 Гаманець {name} ({address}): старий баланс {last_balance} TRX, новий баланс {new_balance} TRX"
        )

        if new_balance != last_balance:  # Перевіряємо, чи змінився баланс
            diff = new_balance - last_balance
            diff_usdt = diff * trx_to_usdt  # Конвертуємо зміну в USDT
            balance_usdt = new_balance * trx_to_usdt  # Поточний баланс у USDT

            if diff > 0:
                message = (
                    f"📥 **Поповнення!**\n"
                    f"🔹 **{name}**\n"
                    f"📍 `{address}`\n"
                    f"💰 +{diff:.2f} TRX (+{diff_usdt:.2f} USDT)\n"
                    f"🏦 Новий баланс: {new_balance:.2f} TRX ≈ {balance_usdt:.2f} USDT"
                )
            else:
                message = (
                    f"📤 **Зняття коштів!**\n"
                    f"🔹 **{name}**\n"
                    f"📍 `{address}`\n"
                    f"💸 {diff:.2f} TRX ({diff_usdt:.2f} USDT)\n"
                    f"🏦 Новий баланс: {new_balance:.2f} TRX ≈ {balance_usdt:.2f} USDT"
                )

            # Отримуємо список підписаних користувачів
            subscribers = await get_subscribers()
            logging.info(f"✉ Надсилаємо сповіщення {len(subscribers)} підписникам")

            for user_id in subscribers:
                try:
                    if diff > 0 or await is_admin(user_id):  # 🔹 Відправляємо зняття тільки адмінам
                        await bot.send_message(user_id, message)
                        logging.info(f"✅ Повідомлення надіслано користувачу {user_id}")
                except Exception as e:
                    logging.error(
                        f"⚠️ Помилка надсилання повідомлення користувачу {user_id}: {e}"
                    )

            # Оновлюємо баланс у базі
            await update_balance(address, new_balance)
            logging.info(f"🔄 Оновлено баланс у базі для {name} ({address})")


@dp.message(Command("total_balance"))
async def total_balance_handler(message: Message):
    """Оновлює баланси та виводить всі гаманці у TRX та USDT"""
    if not await check_access(message):
        return
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    trx_to_usdt = get_trx_to_usdt_rate()  # Отримуємо курс TRX/USDT
    if trx_to_usdt == 0:
        await message.answer("⚠️ Не вдалося отримати курс TRX/USDT. Спробуйте пізніше.")
        return

    wallets = await get_all_wallets()  # Отримуємо всі гаманці
    total_trx = 0
    text = "📊 **Всі гаманці та їх баланси:**\n"

    for name, address, last_balance in wallets:
        balance = get_trx_balance(address)  # Отримуємо актуальний баланс
        await update_balance(address, balance)  # 🔹 Оновлюємо баланс у БД
        balance_usdt = balance * trx_to_usdt  # Конвертуємо TRX → USDT
        total_trx += balance

        text += (
            f"🔹 {name}: `{address}`\n"
            f"💰 {balance:.2f} TRX ≈ {balance_usdt:.2f} USDT\n\n"
        )

    total_usdt = total_trx * trx_to_usdt
    text += f"\n💰 **Загальний баланс:** {total_trx:.2f} TRX ≈ {total_usdt:.2f} USDT"

    await message.answer(text)


@dp.message(Command("set_admin"))
async def set_admin_handler(message: Message):
    """Призначає іншого адміністратора (Доступ тільки для адмінів)"""
    user_id = message.from_user.id

    if not await is_admin(user_id):  # 🔒 Перевіряємо, чи користувач адмін
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
        await asyncio.sleep(5)  # Чекаємо 5 секунд


dp.message(Command("subscribe"))


async def subscribe_handler(message: Message):
    """Додає користувача в список підписників"""
    if not await check_access(message):
        return
    user_id = message.from_user.id
    await add_subscriber(user_id)
    await message.answer("✅ Ви підписані на сповіщення про поповнення!")


@dp.message(Command("pending_users"))
async def pending_users_handler(message: Message):
    """Адмін переглядає список користувачів, які очікують схвалення"""
    user_id = message.from_user.id

    if not await is_admin(user_id):  # 🔒 Доступ лише для адміністраторів
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    from database import get_pending_users

    pending_users = await get_pending_users()  # Отримуємо список користувачів

    if not pending_users:
        await message.answer("✅ Немає користувачів, які очікують схвалення.")
        return

    for user_id, username in pending_users:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Схвалити", callback_data=f"approve:{user_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Відхилити", callback_data=f"reject:{user_id}"
                    )
                ],
            ]
        )

        await message.answer(
            f"👤 **Користувач**: @{username}\n🆔 `{user_id}`", reply_markup=keyboard
        )


@dp.callback_query(lambda c: c.data.startswith("approve:"))
async def approve_user_callback(callback: types.CallbackQuery):
    """Адміністратор схвалює користувача"""
    user_id = int(callback.data.split(":")[1])
    await approve_user(user_id)  # Функція, яка оновлює базу даних

    await bot.send_message(
        user_id, "✅ Вас схвалив адміністратор! Ви тепер можете користуватися ботом."
    )
    await callback.message.edit_text(f"✅ Користувач `{user_id}` схвалений!")
    await callback.answer("✅ Користувач схвалений")


@dp.callback_query(lambda c: c.data.startswith("reject:"))
async def reject_user_callback(callback: types.CallbackQuery):
    """Адміністратор відхиляє користувача"""
    user_id = int(callback.data.split(":")[1])

    from database import remove_user

    await remove_user(user_id)  # Видаляємо користувача з бази

    await callback.message.edit_text(f"❌ Користувач `{user_id}` відхилений.")
    await callback.answer("❌ Користувач відхилений")


@dp.message(Command("approve"))
async def approve_user_handler(message: Message):
    """Схвалює користувача для користування ботом"""
    admin_id = message.from_user.id

    if not await is_admin(admin_id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("❌ Формат команди:\n`/approve user_id`")
        return

    user_id = int(parts[1])
    await approve_user(user_id)
    await message.answer(f"✅ Користувач `{user_id}` тепер має доступ до бота!")


@dp.message(F.text == "📋 Мої гаманці")
async def show_wallets(message: Message):
    if not await check_access(message):
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return
    await wallets_handler(message)


@dp.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    """Обробляє кнопку "Баланс" та викликає основний обробник"""
    if not await check_access(message):
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return
    await balance_handler(message)


@dp.message(F.text == "📊 Загальний баланс")
async def total_balance_button(message: Message):
    if not await check_access(message):
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
    await total_balance_handler(message)


@dp.message(lambda message: message.text == "📊 Загальний баланс")
async def total_balance_button(message: Message):
    if not await check_access(message):
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
    await total_balance_handler(message)


@dp.message(F.text == "⚡ Призначити адміністратора")
async def set_admin_button(message: Message):
    if not await check_access(message):
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
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
    if not await check_access(message):
        return
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Скопіювати команду", callback_data="copy_add_wallet"
                )
            ]
        ]
    )

    await message.answer(
        "✏ **Щоб додати гаманець, введіть команду у форматі:**\n"
        "`/add_wallet Назва Адреса`\n\n"
        "📌 **Натисніть кнопку нижче, щоб отримати команду для копіювання!**",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@dp.message(Command("unsubscribe"))
async def unsubscribe_handler(message: Message):
    """Команда для відписки від сповіщень"""
    user_id = message.from_user.id
    await remove_subscriber(user_id)
    await message.answer(
        "❌ Ви відписалися від сповіщень. Якщо захочете повернутися – скористайтеся командою /subscribe."
    )

    # Оновлення меню після відписки
    menu = await get_main_menu(user_id)
    await message.answer("Оновлено меню:", reply_markup=menu)


@dp.message(F.text == "🔔 Підписатися на сповіщення")
async def subscribe_button_handler(message: Message):
    """Обробляє натискання кнопки '🔔 Підписатися на сповіщення'"""
    await subscribe_handler(message)


@dp.message(F.text == "🔕 Відписатися")
async def unsubscribe_button_handler(message: Message):
    """Обробляє натискання кнопки '🔕 Відписатися'"""
    await unsubscribe_handler(message)


@dp.callback_query(lambda c: c.data.startswith("delete_wallet:"))
async def delete_wallet_callback(callback_query: types.CallbackQuery):
    """Обробник кнопки видалення гаманця"""
    user_id = callback_query.from_user.id
    address = callback_query.data.split(":")[1]

    success = await delete_wallet(user_id, address)

    if success:
        await callback_query.message.edit_text(f"✅ Гаманець `{address}` видалено!")
    else:
        await callback_query.message.answer(
            "⚠️ Помилка видалення гаманця. Можливо, він вже був видалений."
        )

    await callback_query.answer()  # Закриваємо сповіщення


async def main():
    await update_db_schema()  # Додаємо колонку is_subscribed
    print("✅ База даних оновлена!")
    print("✅ Бот запущено")
    await ensure_default_admin()
    asyncio.create_task(scheduled_checker())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
