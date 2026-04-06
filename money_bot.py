import asyncio
import os
import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Состояния
class Form(StatesGroup):
    title = State()
    desc = State()
    budget = State()
    phone = State()

# База данных
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        desc TEXT,
        budget REAL,
        phone TEXT,
        created TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        phone TEXT
    )''')
    conn.commit()
    conn.close()

# Клавиатуры
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Добавить заявку", callback_data="add")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my")],
        [InlineKeyboardButton(text="🔍 Матчи", callback_data="match")]
    ])
    if ADMIN_ID and types.CallbackQuery.from_user.id == ADMIN_ID:
        kb.inline_keyboard.append([InlineKeyboardButton(text="👑 Админ", callback_data="admin")])
    return kb

@dp.message(Command("start"))
async def start(message: Message):
    init_db()
    await message.answer(
        "🚚 <b>ЛОГИСТИКА БОТ</b>\n\n"
        "📦 Добавляй грузы/курьеров\n"
        "🤝 Бот найдёт партнёров\n"
        "💰 Зарабатывай на лидах!",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "add")
async def add_order(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.title)
    await callback.message.edit_text("📦 <b>Новая заявка</b>\n\nНазвание? (Москва-ЕКБ 5т)")

@dp.message(StateFilter(Form.title))
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(Form.desc)
    await message.answer("Описание?\n(вес, маршрут, сроки)")

@dp.message(StateFilter(Form.desc))
async def process_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await state.set_state(Form.budget)
    await message.answer("Бюджет? (15000 руб)")

@dp.message(StateFilter(Form.budget))
async def process_budget(message: Message, state: FSMContext):
    await state.update_data(budget=float(message.text))
    await state.set_state(Form.phone)
    await message.answer("Твой телефон? (+7...)")

@dp.message(StateFilter(Form.phone))
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, title, desc, budget, phone, created) VALUES (?, ?, ?, ?, ?, ?)",
              (message.from_user.id, data['title'], data['desc'], data['budget'], message.text, datetime.now().isoformat()))
    order_id = c.lastrowid
    c.execute("INSERT OR IGNORE INTO users (user_id, phone) VALUES (?, ?)", (message.from_user.id, message.text))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(
        f"✅ <b>Заявка #{order_id}</b>\n\n"
        f"{data['title']}\n"
        f"{data['desc']}\n"
        f"💰 {data['budget']} руб\n"
        f"📞 {message.text}\n\n"
        "Матчинг запущен!",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "my")
async def my_orders(callback: types.CallbackQuery):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT id, title, budget FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", 
              (callback.from_user.id,))
    orders = c.fetchall()
    text = "📋 <b>Твои заявки:</b>\n\n"
    if orders:
        for order in orders:
            text += f"#{order[0]} {order[1]} — {order[2]}р\n"
    else:
        text += "Пока пусто"
    conn.close()
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа!")
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    total = c.fetchone()[0]
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📊 Всего: {total} заявок", callback_data="all")],
        [InlineKeyboardButton(text="📤 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.edit_text("👑 <b>АДМИН ПАНЕЛЬ</b>", reply_markup=kb)

async def main():
    print("🚀 Логистический бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
