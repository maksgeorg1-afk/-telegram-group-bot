import os
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
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
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext


# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8207718857

GROUP_USERNAME = "@vsedlyaludeyukraina"
GROUP_LINK = "https://t.me/vsedlyaludeyukraina"

MAX_ADS_PER_DAY = 5


# =========================================================
# ТЕМЫ ГРУППЫ
# =========================================================

TOPICS = {
    "🛒 Купить": 11316,
    "💰 Продать": 11282,
    "💼 Работа": 11291,
    "🏠 Жильё": 11314,
    "🚗 Авто": 11290,
    "🛠 Услуги": 11313,
    "📦 Другое": 11315,
    "📰 Новости": 11281,
}


# =========================================================
# DISPATCHER
# =========================================================

dp = Dispatcher()


# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(
    "bot_new.db",
    check_same_thread=False
)

cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TEXT NOT NULL
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price TEXT NOT NULL,
    city TEXT NOT NULL,
    contact TEXT NOT NULL,
    photo_id TEXT,
    message_id INTEGER,
    thread_id INTEGER,
    created_at TEXT NOT NULL
)
""")


# Если база была создана старой версией
cursor.execute(
    "PRAGMA table_info(ads)"
)

columns = [
    row[1]
    for row in cursor.fetchall()
]

if "thread_id" not in columns:

    cursor.execute(
        "ALTER TABLE ads ADD COLUMN thread_id INTEGER"
    )

db.commit()


# =========================================================
# СОСТОЯНИЯ
# =========================================================

class AdForm(StatesGroup):
    category = State()
    title = State()
    description = State()
    price = State()
    city = State()
    contact = State()
    photo = State()


class SearchForm(StatesGroup):
    query = State()


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Открыть группу",
                    url=GROUP_LINK
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Купить",
                    callback_data="browse_buy"
                ),
                InlineKeyboardButton(
                    text="💰 Продать",
                    callback_data="browse_sell"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💼 Работа",
                    callback_data="browse_job"
                ),
                InlineKeyboardButton(
                    text="🏠 Жильё",
                    callback_data="browse_home"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚗 Авто",
                    callback_data="browse_auto"
                ),
                InlineKeyboardButton(
                    text="🛠 Услуги",
                    callback_data="browse_services"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Другое",
                    callback_data="browse_other"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔎 Найти объявление",
                    callback_data="search"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Подать объявление",
                    callback_data="new_ad"
                )
            ]
        ]
    )


# =========================================================
# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ
# =========================================================

def register_user(user_id):

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, first_seen)
        VALUES (?, ?)
        """,
        (
            user_id,
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()


# =========================================================
# ОБЪЯВЛЕНИЯ ЗА СЕГОДНЯ
# =========================================================

def ads_today(user_id):

    now = datetime.now(timezone.utc)

    start = datetime(
        now.year,
        now.month,
        now.day,
        tzinfo=timezone.utc
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM ads
        WHERE user_id = ?
        AND created_at >= ?
        """,
        (
            user_id,
            start.isoformat()
        )
    )

    return cursor.fetchone()[0]


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    register_user(
        message.from_user.id
    )

    await message.answer(
        "🇺🇦 <b>UA Объявления</b>\n\n"
        "Здесь можно купить, продать, найти работу, "
        "жильё, авто или услуги.\n\n"
        "Что тебя интересует?",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# /ID
# =========================================================

@dp.message(Command("id"))
async def show_topic_id(
    message: Message
):

    thread_id = message.message_thread_id

    if thread_id is None:

        await message.answer(
            "🆔 Это General."
        )

        return

    await message.answer(
        f"🆔 <b>ID темы:</b> "
        f"<code>{thread_id}</code>",
        parse_mode="HTML"
    )


# =========================================================
# СОЗДАНИЕ ОБЪЯВЛЕНИЯ
# =========================================================

@dp.callback_query(F.data == "new_ad")
async def new_ad(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    user_id = callback.from_user.id

    if ads_today(user_id) >= MAX_ADS_PER_DAY:

        await callback.message.answer(
            "⛔ <b>Лимит достигнут.</b>\n\n"
            f"Максимум — {MAX_ADS_PER_DAY} "
            "объявлений в сутки.",
            parse_mode="HTML"
        )

        return


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Купить",
                    callback_data="adcat_buy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Продать",
                    callback_data="adcat_sell"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💼 Работа",
                    callback_data="adcat_job"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Жильё",
                    callback_data="adcat_home"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚗 Авто",
                    callback_data="adcat_auto"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Услуги",
                    callback_data="adcat_services"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Другое",
                    callback_data="adcat_other"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel"
                )
            ]
        ]
    )


    await callback.message.answer(
        "📢 <b>Новое объявление</b>\n\n"
        "Выбери категорию:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.category
    )


# =========================================================
# ВЫБОР КАТЕГОРИИ
# =========================================================

@dp.callback_query(
    F.data.startswith("adcat_"),
    AdForm.category
)
async def choose_category(
    callback: CallbackQuery,
    state: FSMContext
):

    categories = {
        "adcat_buy": "🛒 Купить",
        "adcat_sell": "💰 Продать",
        "adcat_job": "💼 Работа",
        "adcat_home": "🏠 Жильё",
        "adcat_auto": "🚗 Авто",
        "adcat_services": "🛠 Услуги",
        "adcat_other": "📦 Другое"
    }


    category = categories.get(
        callback.data,
        "📦 Другое"
    )


    await state.update_data(
        category=category
    )

    await callback.answer()


    await callback.message.answer(
        "📝 <b>Шаг 1/6</b>\n\n"
        "Напиши заголовок объявления.\n\n"
        "Например:\n"
        "Продам iPhone 13",
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.title
    )


# =========================================================
# ЗАГОЛОВОК
# =========================================================

@dp.message(AdForm.title)
async def get_title(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❗ Напиши заголовок текстом."
        )

        return


    title = message.text.strip()


    if len(title) < 3:

        await message.answer(
            "❗ Заголовок слишком короткий."
        )

        return


    await state.update_data(
        title=title[:150]
    )


    await message.answer(
        "📝 <b>Шаг 2/6</b>\n\n"
        "Напиши описание объявления.",
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.description
    )


# =========================================================
# ОПИСАНИЕ
# =========================================================

@dp.message(AdForm.description)
async def get_description(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❗ Напиши описание."
        )

        return


    description = message.text.strip()


    if len(description) < 5:

        await message.answer(
            "❗ Описание слишком короткое."
        )

        return


    await state.update_data(
        description=description[:2500]
    )


    await message.answer(
        "💰 <b>Шаг 3/6</b>\n\n"
        "Укажи цену.\n\n"
        "Если цена договорная — напиши "
        "«Договорная».",
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.price
    )


# =========================================================
# ЦЕНА
# =========================================================

@dp.message(AdForm.price)
async def get_price(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❗ Напиши цену."
        )

        return


    await state.update_data(
        price=message.text.strip()[:100]
    )


    await message.answer(
        "📍 <b>Шаг 4/6</b>\n\n"
        "Укажи город.",
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.city
    )


# =========================================================
# ГОРОД
# =========================================================

@dp.message(AdForm.city)
async def get_city(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❗ Напиши город."
        )

        return


    await state.update_data(
        city=message.text.strip()[:100]
    )


    await message.answer(
        "📞 <b>Шаг 5/6</b>\n\n"
        "Укажи контакт для связи.",
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.contact
    )


# =========================================================
# КОНТАКТ
# =========================================================

@dp.message(AdForm.contact)
async def get_contact(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❗ Напиши контакт."
        )

        return


    await state.update_data(
        contact=message.text.strip()[:200]
    )


    await message.answer(
        "📷 <b>Шаг 6/6</b>\n\n"
        "Отправь фотографию объявления.\n\n"
        "Если фото не нужно — напиши "
        "«нет».",
        parse_mode="HTML"
    )


    await state.set_state(
        AdForm.photo
    )


# =========================================================
# ПУБЛИКАЦИЯ
# =========================================================

@dp.message(AdForm.photo)
async def publish_ad(
    message: Message,
    state: FSMContext
):

    photo_id = None


    if message.photo:

        photo_id = message.photo[-1].file_id


    elif message.text:

        if message.text.strip().lower() not in [
            "нет",
            "без фото",
            "no"
        ]:

            await message.answer(
                "📷 Отправь фотографию "
                "или напиши «нет»."
            )

            return


    else:

        await message.answer(
            "📷 Отправь фотографию "
            "или напиши «нет»."
        )

        return


    user_id = message.from_user.id


    if ads_today(user_id) >= MAX_ADS_PER_DAY:

        await state.clear()

        await message.answer(
            "⛔ Дневной лимит достигнут."
        )

        return


    data = await state.get_data()

    category = data["category"]


    thread_id = TOPICS.get(
        category,
        TOPICS["📦 Другое"]
    )


    text = (
        f"{category}\n\n"
        f"📌 <b>{data['title']}</b>\n\n"
        f"{data['description']}\n\n"
        f"💰 Цена: {data['price']}\n"
        f"📍 Город: {data['city']}\n"
        f"📞 Контакт: {data['contact']}\n\n"
        f"🇺🇦 <b>UA Объявления</b>"
    )


    try:

        if photo_id:

            sent = await message.bot.send_photo(
                chat_id=GROUP_USERNAME,
                photo=photo_id,
                caption=text,
                parse_mode="HTML",
                message_thread_id=thread_id
            )

        else:

            sent = await message.bot.send_message(
                chat_id=GROUP_USERNAME,
                text=text,
                parse_mode="HTML",
                message_thread_id=thread_id
            )


        cursor.execute(
            """
            INSERT INTO ads
            (
                user_id,
                category,
                title,
                description,
                price,
                city,
                contact,
                photo_id,
                message_id,
                thread_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                category,
                data["title"],
                data["description"],
                data["price"],
                data["city"],
                data["contact"],
                photo_id,
                sent.message_id,
                thread_id,
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
        )


        ad_id = cursor.lastrowid

        db.commit()

        await state.clear()


        used = ads_today(user_id)

        remaining = (
            MAX_ADS_PER_DAY - used
        )


        delete_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить объявление",
                        callback_data=f"delete_ad:{ad_id}"
                    )
                ]
            ]
        )


        await message.answer(
            "✅ <b>Объявление опубликовано!</b>\n\n"
            f"📍 Раздел: {category}\n"
            f"📢 Сегодня: "
            f"{used}/{MAX_ADS_PER_DAY}\n"
            f"📌 Осталось: {remaining}",
            reply_markup=delete_keyboard,
            parse_mode="HTML"
        )


    except Exception as error:

        print(
            "PUBLICATION ERROR:",
            repr(error)
        )


        await message.answer(
            "❌ <b>Не удалось опубликовать объявление.</b>\n\n"
            "Проверь права бота в группе и ID темы.",
            parse_mode="HTML"
        )


# =========================================================
# УДАЛЕНИЕ ОБЪЯВЛЕНИЯ
# =========================================================

@dp.callback_query(
    F.data.startswith("delete_ad:")
)
async def delete_ad(
    callback: CallbackQuery
):

    try:

        ad_id = int(
            callback.data.split(":")[1]
        )

    except:

        await callback.answer(
            "Ошибка.",
            show_alert=True
        )

        return


    cursor.execute(
        """
        SELECT
            user_id,
            message_id,
            thread_id
        FROM ads
        WHERE id = ?
        """,
        (ad_id,)
    )


    row = cursor.fetchone()


    if not row:

        await callback.answer(
            "Объявление уже удалено.",
            show_alert=True
        )

        return


    owner_id = row[0]

    message_id = row[1]


    if (
        callback.from_user.id != owner_id
        and callback.from_user.id != ADMIN_ID
    ):

        await callback.answer(
            "⛔ Ты не можешь удалить это объявление.",
            show_alert=True
        )

        return


    try:

        await callback.bot.delete_message(
            chat_id=GROUP_USERNAME,
            message_id=message_id
        )

    except Exception as error:

        print(
            "DELETE MESSAGE ERROR:",
            repr(error)
        )


    cursor.execute(
        "DELETE FROM ads WHERE id = ?",
        (ad_id,)
    )

    db.commit()


    await callback.answer(
        "🗑 Объявление удалено."
    )


    try:

        await callback.message.edit_text(
            "🗑 <b>Объявление удалено.</b>",
            parse_mode="HTML"
        )

    except:

        pass


# =========================================================
# ПРОСМОТР КАТЕГОРИЙ
# =========================================================

@dp.callback_query(
    F.data.startswith("browse_")
)
async def browse_category(
    callback: CallbackQuery
):

    categories = {
        "browse_buy": "🛒 Купить",
        "browse_sell": "💰 Продать",
        "browse_job": "💼 Работа",
        "browse_home": "🏠 Жильё",
        "browse_auto": "🚗 Авто",
        "browse_services": "🛠 Услуги",
        "browse_other": "📦 Другое"
    }


    category = categories.get(
        callback.data
    )


    if not category:

        await callback.answer()

        return


    await callback.answer()


    cursor.execute(
        """
        SELECT
            id,
            title,
            description,
            price,
            city
        FROM ads
        WHERE category = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (category,)
    )


    rows = cursor.fetchall()


    if not rows:

        await callback.message.answer(
            f"{category}\n\n"
            "Пока здесь нет объявлений.",
            reply_markup=main_keyboard()
        )

        return


    text = (
        f"{category}\n\n"
        "📋 <b>Последние объявления:</b>\n\n"
    )


    for row in rows:

        ad_id = row[0]
        title = row[1]
        description = row[2]
        price = row[3]
        city = row[4]


        text += (
            f"📌 <b>{title}</b>\n"
            f"💰 {price}\n"
            f"📍 {city}\n"
            f"{description[:120]}\n"
            f"🆔 #{ad_id}\n\n"
        )


    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# ПОИСК
# =========================================================

@dp.callback_query(F.data == "search")
async def search(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()


    await callback.message.answer(
        "🔎 <b>Поиск объявления</b>\n\n"
        "Напиши, что ищешь.\n\n"
        "Например:\n"
        "iPhone\n"
        "водитель\n"
        "квартира\n"
        "велосипед",
        parse_mode="HTML"
    )


    await state.set_state(
        SearchForm.query
    )


# =========================================================
# РЕЗУЛЬТАТЫ ПОИСКА
# =========================================================

@dp.message(SearchForm.query)
async def search_query(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "Напиши запрос текстом."
        )

        return


    query = message.text.strip()


    if len(query) < 2:

        await message.answer(
            "Напиши хотя бы 2 символа."
        )

        return


    pattern = f"%{query}%"


    cursor.execute(
        """
        SELECT
            id,
            category,
            title,
            description,
            price,
            city
        FROM ads
        WHERE
            title LIKE ?
            OR description LIKE ?
            OR city LIKE ?
            OR category LIKE ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (
            pattern,
            pattern,
            pattern,
            pattern
        )
    )


    rows = cursor.fetchall()


    await state.clear()


    if not rows:

        await message.answer(
            "🔎 Ничего не найдено.",
            reply_markup=main_keyboard()
        )

        return


    text = (
        "🔎 <b>Результаты поиска:</b>\n\n"
    )


    for row in rows:

        ad_id = row[0]
        category = row[1]
        title = row[2]
        description = row[3]
        price = row[4]
        city = row[5]


        text += (
            f"{category}\n"
            f"📌 <b>{title}</b>\n"
            f"💰 {price}\n"
            f"📍 {city}\n"
            f"{description[:120]}\n"
            f"🆔 #{ad_id}\n\n"
        )


    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# ОТМЕНА
# =========================================================

@dp.callback_query(F.data == "cancel")
async def cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.answer()

    await callback.message.answer(
        "❌ Создание объявления отменено.",
        reply_markup=main_keyboard()
    )


# =========================================================
# АДМИН-ПАНЕЛЬ
# =========================================================

@dp.message(Command("admin"))
async def admin(
    message: Message
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Доступ запрещён."
        )

        return


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats"
                )
            ]
        ]
    )


    await message.answer(
        "🛠 <b>Админ-панель</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# =========================================================
# СТАТИСТИКА
# =========================================================

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )

        return


    await callback.answer()


    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COUNT(*) FROM ads"
    )

    total_ads = cursor.fetchone()[0]


    now = datetime.now(timezone.utc)


    day = now - timedelta(days=1)

    week = now - timedelta(days=7)

    month = now - timedelta(days=30)


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM ads
        WHERE created_at >= ?
        """,
        (day.isoformat(),)
    )

    day_ads = cursor.fetchone()[0]


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM ads
        WHERE created_at >= ?
        """,
        (week.isoformat(),)
    )

    week_ads = cursor.fetchone()[0]


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM ads
        WHERE created_at >= ?
        """,
        (month.isoformat(),)
    )

    month_ads = cursor.fetchone()[0]


    await callback.message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {users}\n"
        f"📢 Объявлений: {total_ads}\n\n"
        f"🟢 За 24 часа: {day_ads}\n"
        f"🟡 За 7 дней: {week_ads}\n"
        f"🟠 За 30 дней: {month_ads}",
        parse_mode="HTML"
    )


# =========================================================
# RENDER WEB SERVER
# =========================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(200)

        self.end_headers()

        self.wfile.write(
            b"UA Announcements Bot is running"
        )


    def log_message(
        self,
        format,
        *args
    ):
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


# =========================================================
# MAIN
# =========================================================

async def main():

    Thread(
        target=run_web_server,
        daemon=True
    ).start()


    if not TOKEN:

        print(
            "ERROR: BOT_TOKEN is missing!"
        )

        return


    bot = Bot(
        token=TOKEN
    )


    print(
        "🇺🇦 UA Announcements Bot started!"
    )


    await dp.start_polling(
        bot
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())
