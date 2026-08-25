import os
import asyncio
import sqlite3
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)


# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")

GROUP_LINK = "https://t.me/vsedlyaludeyukraina"

BOT_USERNAME = "MyGroupJoinBot"

ADMIN_ID = 8207718857


# =========================
# BOT
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
# ADMIN MENU
# =========================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="stats"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔗 Моя ссылка",
                    callback_data="link"
                )
            ],

            [
                InlineKeyboardButton(
                    text="👥 Вступления",
                    callback_data="members"
                )
            ],

            [
                InlineKeyboardButton(
                    text="ℹ️ Информация",
                    callback_data="info"
                )
            ]

        ]
    )


# =========================
# /ADMIN
# =========================

@dp.message(Command("admin"))
async def admin(message: Message):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ У вас нет доступа."
        )

        return

    await message.answer(
        "🛠 Панель управления\n\n"
        "Выбери нужный раздел:",
        reply_markup=admin_keyboard()
    )


# =========================
# /START
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
# НОВЫЙ УЧАСТНИК
# =========================

@dp.chat_member()
async def chat_member_update(event):

    if event.new_chat_member.status == "member":

        user_id = event.new_chat_member.user.id

        cursor.execute(
            """
            INSERT OR IGNORE INTO group_members
            (user_id)
            VALUES (?)
            """,
            (user_id,)
        )

        db.commit()

        print(
            f"New member: {user_id}"
        )


# =========================
# СТАТИСТИКА
# =========================

async def show_stats(message):

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    bot_users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM group_members"
    )

    members = cursor.fetchone()[0]

    await message.answer(
        "📊 Статистика\n\n"
        f"🤖 Запустили бота: {bot_users}\n"
        f"👥 Зафиксировано вступлений: {members}"
    )


# =========================
# КНОПКА СТАТИСТИКА
# =========================

@dp.callback_query(F.data == "stats")
async def stats_button(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await callback.answer()

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    bot_users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM group_members"
    )

    members = cursor.fetchone()[0]

    await callback.message.answer(
        "📊 Статистика\n\n"
        f"🤖 Запустили бота: {bot_users}\n"
        f"👥 Зафиксировано вступлений: {members}"
    )


# =========================
# КНОПКА ССЫЛКА
# =========================

@dp.callback_query(F.data == "link")
async def link_button(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await callback.answer()

    link = f"https://t.me/{BOT_USERNAME}?start=promo"

    await callback.message.answer(
        "🔗 Твоя ссылка:\n\n"
        f"{link}"
    )


# =========================
# КНОПКА ВСТУПЛЕНИЯ
# =========================

@dp.callback_query(F.data == "members")
async def members_button(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await callback.answer()

    cursor.execute(
        "SELECT COUNT(*) FROM group_members"
    )

    members = cursor.fetchone()[0]

    await callback.message.answer(
        "👥 Вступления\n\n"
        f"Зафиксировано новых вступлений: {members}"
    )


# =========================
# ИНФОРМАЦИЯ
# =========================

@dp.callback_query(F.data == "info")
async def info_button(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    await callback.answer()

    await callback.message.answer(
        "ℹ️ Информация\n\n"
        "🤖 Бот: @MyGroupJoinBot\n"
        "👥 Группа: @vsedlyaludeyukraina\n\n"
        "🔗 Основная ссылка:\n"
        "https://t.me/MyGroupJoinBot?start=promo"
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
