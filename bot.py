import os
import asyncio
import sqlite3
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")

GROUP_LINK = "https://t.me/vsedlyaludeyukraina"

# Твой Telegram ID
ADMIN_ID = 8207718857


# =========================
# TELEGRAM BOT
# =========================

dp = Dispatcher()


# =========================
# DATABASE
# =========================

db = sqlite3.connect(
    "stats.db",
    check_same_thread=False
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    UNIQUE(user_id, source)
)
""")

db.commit()


# =========================
# /START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    args = message.text.split(maxsplit=1)

    source = "direct"

    if len(args) > 1:
        source = args[1][:100]

    user_id = message.from_user.id

    cursor.execute(
        """
        INSERT OR IGNORE INTO visits
        (user_id, source)
        VALUES (?, ?)
        """,
        (user_id, source)
    )

    db.commit()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Вступить в группу",
                    url=GROUP_LINK
                )
            ]
        ]
    )

    await message.answer(
        "Привет! 👋\n\n"
        "Нажми кнопку ниже, чтобы перейти в нашу группу:",
        reply_markup=keyboard
    )


# =========================
# /STATS
# =========================

@dp.message(Command("stats"))
async def stats(message: Message):

    # Проверяем, что команду отправил владелец
    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ У вас нет доступа к статистике."
        )

        return

    cursor.execute("""
        SELECT source, COUNT(*)
        FROM visits
        GROUP BY source
        ORDER BY COUNT(*) DESC
    """)

    rows = cursor.fetchall()

    if not rows:

        await message.answer(
            "📊 Пока переходов нет."
        )

        return

    text = "📊 Статистика переходов:\n\n"

    total = 0

    for source, count in rows:

        text += f"🔹 {source}: {count}\n"

        total += count

    text += f"\n👥 Всего: {total}"

    await message.answer(text)


# =========================
# WEB SERVER ДЛЯ RENDER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.end_headers()

        self.wfile.write(
            b"Telegram bot is running"
        )

    def log_message(self, format, *args):
        pass


def run_web_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    server.serve_forever()


# =========================
# ЗАПУСК
# =========================

async def main():

    # Запускаем веб-сервер для Render
    Thread(
        target=run_web_server,
        daemon=True
    ).start()

    # Проверяем наличие токена
    if not TOKEN:

        print(
            "ERROR: BOT_TOKEN is not set"
        )

        return

    bot = Bot(
        token=TOKEN
    )

    print(
        "Telegram bot started"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
