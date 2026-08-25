import os
import asyncio
import sqlite3
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta, timezone

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
    first_seen TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS group_members (
    user_id INTEGER PRIMARY KEY,
    joined_at TEXT
)
""")


db.commit()


# =========================
# TIME
# =========================

def now_utc():
    return datetime.now(timezone.utc)


def today_start():
    now = now_utc()

    return datetime(
        now.year,
        now.month,
        now.day,
        tzinfo=timezone.utc
    )


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
# ФУНКЦИЯ СТАТИСТИКИ
# =========================

def get_stats():

    now = now_utc()

    day_ago = now - timedelta(days=1)

    week_ago = now - timedelta(days=7)

    month_ago = now - timedelta(days=30)


    # Всего запусков
    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]


    # Всего вступлений
    cursor.execute(
        "SELECT COUNT(*) FROM group_members"
    )

    total_members = cursor.fetchone()[0]


    # Запуски за сутки
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE first_seen >= ?
        """,
        (day_ago.isoformat(),)
    )

    day_users = cursor.fetchone()[0]


    # Запуски за неделю
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE first_seen >= ?
        """,
        (week_ago.isoformat(),)
    )

    week_users = cursor.fetchone()[0]


    # Запуски за месяц
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE first_seen >= ?
        """,
        (month_ago.isoformat(),)
    )

    month_users = cursor.fetchone()[0]


    # Вступления за сутки
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM group_members
        WHERE joined_at >= ?
        """,
        (day_ago.isoformat(),)
    )

    day_members = cursor.fetchone()[0]


    # Вступления за неделю
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM group_members
        WHERE joined_at >= ?
        """,
        (week_ago.isoformat(),)
    )

    week_members = cursor.fetchone()[0]


    # Вступления за месяц
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM group_members
        WHERE joined_at >= ?
        """,
        (month_ago.isoformat(),)
    )

    month_members = cursor.fetchone()[0]


    # Конверсия
    if total_users > 0:

        conversion = (
            total_members / total_users
        ) * 100

    else:

        conversion = 0


    return (
        total_users,
        total_members,
        day_users,
        day_members,
        week_users,
        week_members,
        month_users,
        month_members,
        conversion
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

    current_time = now_utc().isoformat()


    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, first_seen)
        VALUES (?, ?)
        """,
        (
            user_id,
            current_time
        )
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

        current_time = now_utc().isoformat()


        cursor.execute(
            """
            INSERT OR IGNORE INTO group_members
            (user_id, joined_at)
            VALUES (?, ?)
            """,
            (
                user_id,
                current_time
            )
        )


        db.commit()


        print(
            f"New member: {user_id}"
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


    (
        total_users,
        total_members,
        day_users,
        day_members,
        week_users,
        week_members,
        month_users,
        month_members,
        conversion
    ) = get_stats()


    text = (
        "📊 Статистика\n\n"

        "🔵 ВСЁ ВРЕМЯ\n"
        f"🤖 Запустили бота: {total_users}\n"
        f"👥 Вступили: {total_members}\n\n"

        "🟢 ПОСЛЕДНИЕ 24 ЧАСА\n"
        f"🤖 Запустили: {day_users}\n"
        f"👥 Вступили: {day_members}\n\n"

        "🟡 ПОСЛЕДНИЕ 7 ДНЕЙ\n"
        f"🤖 Запустили: {week_users}\n"
        f"👥 Вступили: {week_members}\n\n"

        "🟠 ПОСЛЕДНИЕ 30 ДНЕЙ\n"
        f"🤖 Запустили: {month_users}\n"
        f"👥 Вступили: {month_members}\n\n"

        f"📈 Общая конверсия: {conversion:.1f}%"
    )


    await callback.message.answer(text)


# =========================
# СТАТИСТИКА ВСТУПЛЕНИЙ
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
        f"Всего зафиксировано: {members}"
    )


# =========================
# ССЫЛКА
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


    link = (
        f"https://t.me/"
        f"{BOT_USERNAME}"
        f"?start=promo"
    )


    await callback.message.answer(
        "🔗 Твоя ссылка:\n\n"
        f"{link}"
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
        "🔗 Ссылка:\n"
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
        (
            "0.0.0.0",
            port
        ),
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
