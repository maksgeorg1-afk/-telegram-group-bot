import os
import sqlite3
import asyncio
import random
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


cursor.execute("PRAGMA table_info(ads)")

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
# ИГРОВЫЕ СОСТОЯНИЯ
# =========================================================

snake_games = {}
tetris_games = {}


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
                    text="🎮 ИГРЫ",
                    callback_data="games"
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
# МЕНЮ ИГР
# =========================================================

def games_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧱 ТЕТРИС",
                    callback_data="game_tetris"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🐍 ЗМЕЙКА",
                    callback_data="game_snake"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="back_main"
                )
            ]
        ]
    )


# =========================================================
# РЕГИСТРАЦИЯ
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
# START
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
        "🎮 А ещё у нас появились игры!\n\n"
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
# ИГРЫ
# =========================================================

@dp.callback_query(F.data == "games")
async def games_menu(
    callback: CallbackQuery
):

    await callback.answer()

    await callback.message.answer(
        "🎮 <b>ИГРОВОЙ ЦЕНТР</b>\n\n"
        "Выбирай игру и попробуй побить свой рекорд! 🏆\n\n"
        "🧱 <b>Тетрис</b> — собирай линии\n"
        "🐍 <b>Змейка</b> — собирай яблоки\n\n"
        "🔥 Чем больше очков — тем лучше!",
        reply_markup=games_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# НАЗАД
# =========================================================

@dp.callback_query(F.data == "back_main")
async def back_main(
    callback: CallbackQuery
):

    await callback.answer()

    await callback.message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# =========================================================
# ЗМЕЙКА
# =========================================================
# =========================================================

SNAKE_WIDTH = 10
SNAKE_HEIGHT = 12


def snake_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬆️",
                    callback_data="snake_up"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data="snake_left"
                ),
                InlineKeyboardButton(
                    text="⏹️",
                    callback_data="snake_stop"
                ),
                InlineKeyboardButton(
                    text="➡️",
                    callback_data="snake_right"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬇️",
                    callback_data="snake_down"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Новая игра",
                    callback_data="game_snake"
                ),
                InlineKeyboardButton(
                    text="🎮 Игры",
                    callback_data="games"
                )
            ]
        ]
    )


def create_snake(user_id):

    snake = [
        (5, 6),
        (4, 6),
        (3, 6)
    ]

    food = create_snake_food(snake)

    snake_games[user_id] = {
        "snake": snake,
        "food": food,
        "direction": (1, 0),
        "next_direction": (1, 0),
        "score": 0,
        "running": True,
        "game_over": False
    }


def create_snake_food(snake):

    empty = []

    for y in range(SNAKE_HEIGHT):
        for x in range(SNAKE_WIDTH):

            if (x, y) not in snake:
                empty.append((x, y))

    if not empty:
        return None

    return random.choice(empty)


def render_snake(game):

    snake = game["snake"]
    food = game["food"]

    result = []

    result.append(
        "🐍 <b>ЗМЕЙКА</b>\n"
        "━━━━━━━━━━━━\n"
        f"🏆 Очки: <b>{game['score']}</b>\n\n"
    )

    for y in range(SNAKE_HEIGHT):

        line = ""

        for x in range(SNAKE_WIDTH):

            pos = (x, y)

            if pos == snake[0]:
                line += "🐲"

            elif pos in snake:
                line += "🟢"

            elif pos == food:
                line += "🍎"

            else:
                line += "⬛"

        result.append(line + "\n")

    result.append(
        "\n🎯 Собирай 🍎 и не врезайся!"
    )

    return "".join(result)


async def snake_loop(
    bot,
    chat_id,
    user_id,
    message_id
):

    while user_id in snake_games:

        game = snake_games[user_id]

        if not game["running"]:
            break

        await asyncio.sleep(0.65)

        if user_id not in snake_games:
            break

        game = snake_games[user_id]

        if not game["running"]:
            break

        game["direction"] = game["next_direction"]

        head = game["snake"][0]

        dx, dy = game["direction"]

        new_head = (
            head[0] + dx,
            head[1] + dy
        )

        hit_wall = (
            new_head[0] < 0
            or new_head[0] >= SNAKE_WIDTH
            or new_head[1] < 0
            or new_head[1] >= SNAKE_HEIGHT
        )

        hit_self = new_head in game["snake"]

        if hit_wall or hit_self:

            game["running"] = False
            game["game_over"] = True

            try:

                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=(
                        "💥 <b>ИГРА ОКОНЧЕНА!</b>\n\n"
                        "🐍 Змейка врезалась!\n\n"
                        f"🏆 Твой результат: "
                        f"<b>{game['score']}</b>\n\n"
                        "🔥 Попробуешь ещё раз?"
                    ),
                    reply_markup=snake_keyboard(),
                    parse_mode="HTML"
                )

            except Exception as error:

                print(
                    "SNAKE GAME OVER:",
                    repr(error)
                )

            break

        game["snake"].insert(
            0,
            new_head
        )

        if new_head == game["food"]:

            game["score"] += 10

            game["food"] = create_snake_food(
                game["snake"]
            )

        else:

            game["snake"].pop()

        try:

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=render_snake(game),
                reply_markup=snake_keyboard(),
                parse_mode="HTML"
            )

        except Exception as error:

            print(
                "SNAKE UPDATE:",
                repr(error)
            )

            break


@dp.callback_query(F.data == "game_snake")
async def start_snake(
    callback: CallbackQuery
):

    await callback.answer()

    user_id = callback.from_user.id

    create_snake(user_id)

    game = snake_games[user_id]

    sent = await callback.message.answer(
        render_snake(game),
        reply_markup=snake_keyboard(),
        parse_mode="HTML"
    )

    asyncio.create_task(
        snake_loop(
            callback.bot,
            sent.chat.id,
            user_id,
            sent.message_id
        )
    )


# =========================================================
# УПРАВЛЕНИЕ ЗМЕЙКОЙ
# =========================================================

@dp.callback_query(F.data.startswith("snake_"))
async def snake_controls(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if user_id not in snake_games:

        await callback.answer(
            "Сначала запусти игру!",
            show_alert=True
        )

        return

    game = snake_games[user_id]

    if game["game_over"]:

        await callback.answer(
            "Игра окончена! Нажми 🔄 Новая игра.",
            show_alert=True
        )

        return

    directions = {

        "snake_up": (0, -1),

        "snake_down": (0, 1),

        "snake_left": (-1, 0),

        "snake_right": (1, 0)
    }

    if callback.data == "snake_stop":

        game["running"] = not game["running"]

        if game["running"]:

            await callback.answer(
                "▶️ Игра продолжена!"
            )

        else:

            await callback.answer(
                "⏸ Игра поставлена на паузу."
            )

        return

    new_direction = directions.get(
        callback.data
    )

    if new_direction:

        current = game["direction"]

        # Запрещаем разворот на 180 градусов
        if (
            new_direction[0] != -current[0]
            or new_direction[1] != -current[1]
        ):

            game["next_direction"] = new_direction

        await callback.answer()


# =========================================================
# =========================================================
# ТЕТРИС
# =========================================================
# =========================================================

TETRIS_WIDTH = 10
TETRIS_HEIGHT = 16

EMPTY = "⬛"

TETRIS_BLOCKS = [
    "🟥",
    "🟦",
    "🟩",
    "🟨",
    "🟪",
    "🟧",
    "🔵"
]


TETROMINOES = [

    [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)]
    ],

    [
        [(0, 0), (1, 0), (0, 1), (1, 1)]
    ],

    [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)]
    ],

    [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)]
    ],

    [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)]
    ],

    [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)]
    ],

    [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(1, 0), (0, 1), (1, 1), (0, 2)]
    ]
]


def create_tetris_board():

    return [
        [EMPTY for _ in range(TETRIS_WIDTH)]
        for _ in range(TETRIS_HEIGHT)
    ]


def create_tetris_piece():

    piece_id = random.randrange(
        len(TETROMINOES)
    )

    return {
        "type": piece_id,
        "rotation": 0,
        "x": 3,
        "y": 0,
        "emoji": TETRIS_BLOCKS[
            piece_id
        ]
    }


def piece_cells(piece):

    rotations = TETROMINOES[
        piece["type"]
    ]

    rotation = (
        piece["rotation"]
        % len(rotations)
    )

    return rotations[rotation]


def valid_tetris_position(
    game,
    piece,
    dx=0,
    dy=0,
    rotation=None
):

    board = game["board"]

    if rotation is None:

        rotation = piece["rotation"]

    rotations = TETROMINOES[
        piece["type"]
    ]

    cells = rotations[
        rotation % len(rotations)
    ]

    for px, py in cells:

        x = piece["x"] + px + dx
        y = piece["y"] + py + dy

        if x < 0 or x >= TETRIS_WIDTH:
            return False

        if y >= TETRIS_HEIGHT:
            return False

        if y >= 0:

            if board[y][x] != EMPTY:
                return False

    return True


def place_tetris_piece(game):

    piece = game["piece"]

    for px, py in piece_cells(piece):

        x = piece["x"] + px
        y = piece["y"] + py

        if (
            0 <= y < TETRIS_HEIGHT
            and 0 <= x < TETRIS_WIDTH
        ):

            game["board"][y][x] = piece["emoji"]


def clear_tetris_lines(game):

    board = game["board"]

    new_board = []

    cleared = 0

    for row in board:

        if all(
            cell != EMPTY
            for cell in row
        ):

            cleared += 1

        else:

            new_board.append(row)

    while len(new_board) < TETRIS_HEIGHT:

        new_board.insert(
            0,
            [EMPTY] * TETRIS_WIDTH
        )

    game["board"] = new_board

    if cleared == 1:
        game["score"] += 100

    elif cleared == 2:
        game["score"] += 300

    elif cleared == 3:
        game["score"] += 600

    elif cleared >= 4:
        game["score"] += 1000


def tetris_display_board(game):

    board = [
        row.copy()
        for row in game["board"]
    ]

    piece = game["piece"]

    for px, py in piece_cells(piece):

        x = piece["x"] + px
        y = piece["y"] + py

        if (
            0 <= x < TETRIS_WIDTH
            and 0 <= y < TETRIS_HEIGHT
        ):

            board[y][x] = piece["emoji"]

    lines = []

    for row in board:

        lines.append(
            "".join(row)
        )

    return "\n".join(lines)


def render_tetris(game):

    level = (
        game["score"] // 500
    ) + 1

    return (
        "🧱 <b>Т Е Т Р И С</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Очки: <b>{game['score']}</b>   "
        f"⚡ Уровень: <b>{level}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{tetris_display_board(game)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⬅️ ➡️ движение\n"
        "🔄 поворот\n"
        "⬇️ ускорить падение\n"
        "⏬ бросить вниз"
    )


def tetris_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data="tetris_left"
                ),
                InlineKeyboardButton(
                    text="🔄",
                    callback_data="tetris_rotate"
                ),
                InlineKeyboardButton(
                    text="➡️",
                    callback_data="tetris_right"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬇️ ПАДЕНИЕ",
                    callback_data="tetris_down"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏬ СБРОС",
                    callback_data="tetris_drop"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Новая игра",
                    callback_data="game_tetris"
                ),
                InlineKeyboardButton(
                    text="🎮 Игры",
                    callback_data="games"
                )
            ]
        ]
    )


def create_tetris(user_id):

    tetris_games[user_id] = {
        "board": create_tetris_board(),
        "piece": create_tetris_piece(),
        "score": 0,
        "running": True,
        "game_over": False
    }


async def tetris_loop(
    bot,
    chat_id,
    user_id,
    message_id
):

    while user_id in tetris_games:

        game = tetris_games[user_id]

        if not game["running"]:
            break

        score = game["score"]

        # Чем выше уровень, тем быстрее
        delay = max(
            0.18,
            0.75 - (score // 500) * 0.06
        )

        await asyncio.sleep(delay)

        if user_id not in tetris_games:
            break

        game = tetris_games[user_id]

        if not game["running"]:
            break

        piece = game["piece"]

        if valid_tetris_position(
            game,
            piece,
            dy=1
        ):

            piece["y"] += 1

        else:

            place_tetris_piece(game)

            clear_tetris_lines(game)

            game["piece"] = create_tetris_piece()

            if not valid_tetris_position(
                game,
                game["piece"]
            ):

                game["running"] = False
                game["game_over"] = True

                try:

                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=(
                            "💥 <b>ТЕТРИС ОКОНЧЕН!</b>\n\n"
                            f"🏆 Твой результат: "
                            f"<b>{game['score']}</b>\n\n"
                            "🔥 Сможешь набрать больше?"
                        ),
                        reply_markup=tetris_keyboard(),
                        parse_mode="HTML"
                    )

                except Exception as error:

                    print(
                        "TETRIS GAME OVER:",
                        repr(error)
                    )

                break

        try:

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=render_tetris(game),
                reply_markup=tetris_keyboard(),
                parse_mode="HTML"
            )

        except Exception as error:

            print(
                "TETRIS UPDATE:",
                repr(error)
            )

            break


@dp.callback_query(F.data == "game_tetris")
async def start_tetris(
    callback: CallbackQuery
):

    await callback.answer()

    user_id = callback.from_user.id

    create_tetris(user_id)

    game = tetris_games[user_id]

    sent = await callback.message.answer(
        render_tetris(game),
        reply_markup=tetris_keyboard(),
        parse_mode="HTML"
    )

    asyncio.create_task(
        tetris_loop(
            callback.bot,
            sent.chat.id,
            user_id,
            sent.message_id
        )
    )


# =========================================================
# УПРАВЛЕНИЕ ТЕТРИСОМ
# =========================================================

@dp.callback_query(F.data.startswith("tetris_"))
async def tetris_controls(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if user_id not in tetris_games:

        await callback.answer(
            "Сначала запусти Тетрис!",
            show_alert=True
        )

        return

    game = tetris_games[user_id]

    if game["game_over"]:

        await callback.answer(
            "Игра окончена! Нажми 🔄 Новая игра.",
            show_alert=True
        )

        return

    piece = game["piece"]

    if callback.data == "tetris_left":

        if valid_tetris_position(
            game,
            piece,
            dx=-1
        ):

            piece["x"] -= 1

        await callback.answer()

    elif callback.data == "tetris_right":

        if valid_tetris_position(
            game,
            piece,
            dx=1
        ):

            piece["x"] += 1

        await callback.answer()

    elif callback.data == "tetris_down":

        if valid_tetris_position(
            game,
            piece,
            dy=1
        ):

            piece["y"] += 1

            game["score"] += 1

        await callback.answer()

    elif callback.data == "tetris_rotate":

        new_rotation = (
            piece["rotation"] + 1
        )

        if valid_tetris_position(
            game,
            piece,
            rotation=new_rotation
        ):

            piece["rotation"] = new_rotation

        await callback.answer()

    elif callback.data == "tetris_drop":

        distance = 0

        while valid_tetris_position(
            game,
            piece,
            dy=1
        ):

            piece["y"] += 1

            distance += 1

        game["score"] += distance * 2

        await callback.answer(
            "⏬ БАМ!"
        )

    try:

        await callback.message.edit_text(
            render_tetris(game),
            reply_markup=tetris_keyboard(),
            parse_mode="HTML"
        )

    except Exception as error:

        print(
            "TETRIS BUTTON UPDATE:",
            repr(error)
        )


# =========================================================
# =========================================================
# ОБЪЯВЛЕНИЯ
# =========================================================
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
# КАТЕГОРИЯ
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
# УДАЛЕНИЕ
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
# АДМИН
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
# WEB SERVER
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
