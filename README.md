# 🏦 Crypto Wallet Monitoring Bot

**Телеграм-бот для моніторингу балансу криптовалютних гаманців (USDT TRC-20, BTC, SOL та ін.)**

## 🚀 Опис

Цей бот автоматично перевіряє баланс заданих крипто-гаманців та надсилає повідомлення при зміні балансу. Використовує API TronScan та інші сервіси для отримання актуальних даних.

## 🔥 Основні функції

- ✅ **Автоматичний моніторинг** – перевірка балансу всіх доданих гаманців у фоновому режимі.
- ✅ **Сповіщення** – надсилає повідомлення у Telegram при зміні балансу.
- ✅ **Підтримка декількох валют** – працює з TRC-20 (USDT), BTC, SOL тощо.
- ✅ **Панель адміністратора** – можливість додавання нових гаманців для моніторингу.
- ✅ **Кастомні налаштування** – адміністратор може керувати користувачами та їх доступами.

---

## 📦 Встановлення та запуск

### 1️⃣ Клонування репозиторію

```bash
git clone https://github.com/yourusername/CriptoTgBot.git
cd CriptoTgBot
```

### 2️⃣ Створення віртуального середовища

```bash
python3 -m venv venv
source venv/bin/activate  # Для Linux та MacOS
venv\Scripts\activate  # Для Windows
```

### 3️⃣ Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4️⃣ Налаштування `.env` (змінні середовища)

Створіть файл `.env` у кореневій директорії та додайте наступні параметри:

```ini
# 🔐 Telegram Bot Token (отримайте в @BotFather)
BOT_TOKEN=your_bot_token_here

# 👑 ID Адміністратора (замініть на ваш Telegram ID)
DEFAULT_ADMIN_ID=your_admin_id_here

# 🗄️ Назва файлу бази даних
DB_NAME=wallets.db

# 🔗 API URL для отримання балансу з Tronscan (безпеки ради URL можна змінювати)
TRONSCAN_API_URL=https://apilist.tronscan.org/api/account?address=
```

### 5️⃣ Запуск бота

```bash
python bot.py
```

---

## 🛠 Технології

- **Python 3.12**
- **Aiogram 3.0** – для інтеграції з Telegram
- **SQLite/PostgreSQL** – для збереження даних
- **TronScan API** – для перевірки балансу гаманців

---

## 🔄 Деплой на сервер (Linux, VPS)

Якщо хочете запускати бота **24/7** на сервері:

```bash
nohup python bot.py &
```

Або використовуйте **PM2**:

```bash
pip install pm2
pm2 start bot.py --name "CryptoBot"
pm2 save
pm2 startup
```

---

## 🤝 Контакти

- **Автор:** bamagama228
- **GitHub:** [AndriZhok](https://github.com/AndriZhok)

🔗 **Ліцензія:** MIT License

🚀 _Розробка триває! Будь ласка, створюйте issue, якщо знайдете помилки або маєте пропозиції!_