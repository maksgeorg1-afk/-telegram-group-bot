import os
import asyncio
import sqlite3
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")

GROUP_LINK = "https://t.me/vsedlyaludeyukraina"

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
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS group_members (
    user_id INTEGER PRIMARY KEY,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    cursor.execute(
        """
        INSERT OR IGNORE INTO users (user_id)
        VALUES (?)
        """,
        (user_id,)
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
        "Добро пожаловать!\n\n"
        "Нажми кнопку ниже, чтобы перейти в нашу группу:",
        reply_markup=keyboard
    )


# =========================
# ОТСЛЕЖИВАНИЕ НОВЫХ УЧАСТНИКОВ
# =========================

@dp.chat_member()
async def chat_member_update(event):

    new_member = event.new_chat_member

    if new_member.status == "member":

        user_id = new_member.user.id

        cursor.execute(
            """
            INSERT OR IGNORE INTO group_members (user_id)
            VALUES (?)
            """,
            (user_id,)
        )

        db.commit()

        print(
            f"New group member: {user_id}"
        )


# =========================
# СТАТИСТИКА
# =========================

@dp.message(Command("stats"))
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ У вас нет доступа к статистике."
        )

        return

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    bot_users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM group_members"
    )

    group_members = cursor.fetchone()[0]

    await message.answer(
        "📊 Статистика\n\n"
        f"🤖 Запустили бота: {bot_users}\n"
        f"👥 Зафиксировано новых вступлений: {group_members}"
    )


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

    Thread(
        target=run_web_server,
        daemon=True
    ).start()

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
