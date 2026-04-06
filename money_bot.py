import asyncio
import logging
import os
import sqlite3
import csv
import io
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Состояния FSM
class Form(StatesGroup):
    role = State()
    title = State()
    desc = State()
    budget = State()
    phone = State()

# Инициализация БД
def init_db():
    conn = sqlite3.connect('logistics.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        role TEXT,
        phone TEXT,
        region TEXT DEFAULT 'ЕКБ'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        title TEXT,
        description TEXT,
        budget REAL,
        status TEXT DEFAULT 'active',
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
        order_id INTEGER,
        supplier_id INTEGER
    )''')
    conn.commit()
    conn.close()

# Клавиатуры
def main_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Добавить заявку", callback_data="add_order")],
        [InlineKeyboardButton(text="🔍 Мои заявки", callback_data="my_orders")],
        [InlineKeyboardButton(text="🤝 Матчи", callback_data="matches")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])
    if user_id == ADMIN_ID:
        kb.inline_keyboard.append([InlineKeyboardButton(text="👨‍💼 Админ", callback_data="admin")])
    return kb

def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="all_orders")],
        [InlineKeyboardButton(text="📤 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="📊 Экспорт CSV", callback_data="export_csv")],
        [InlineKeyboardButton(text="🔙 Главное", callback_data="back_main")]
    ])

# Команды
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect('logistics.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, role) VALUES (?, ?)", (user_id, 'client'))
    conn.commit()
    conn.close()
    await message.answer(
        f"🚚 <b>Логистический бот для {message.from_user.first_name}</b>\n\n"
        "Добавляй заявки на грузы/курьеров — бот найдёт партнёров!\n"
        "Регион: ЕКБ (меняй /setregion).",
        reply_markup=main_kb(user_id)
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "📋 <b>Команды:</b>\n"
        "/start — главное меню\n"
        "/myorders — твои заявки\n"
        "/stats — статистика\n"
        "Админ: /admin\n\n"
        "💎 Премиум: unlimited матчи (добавь позже)"
    )

@dp.message(Command("setregion"))
async def set_region(message: types.Message):
    await message.answer("Новый регион? (ЕКБ, МСК...)")
    # Добавь FSM для региона

# Callbacks
@dp.callback_query(F.data == "add_order")
async def add_order(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.role)
    await callback.message.edit_text("Ты клиент (груз) или поставщик (курьер)?\n<b>client/supplier</b>", reply_markup=None)
    await callback.answer()

@dp.message(StateFilter(Form.role))
async def process_role(message: types.Message, state: FSMContext):
    await state.update_data(role=message.text.lower())
    await state.set_state(Form.title)
    await message.answer("Название заявки? (Груз Москва-ЕКБ)")

@dp.message(StateFilter(Form.title))
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(Form.desc)
    await message.answer("Описание? (Вес, маршрут, сроки)")

@dp.message(StateFilter(Form.desc))
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(Form.budget)
    await message.answer("Бюджет? (10000 руб)")

@dp.message(StateFilter(Form.budget))
async def process_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=float(message.text))
    await state.set_state(Form.phone)
    await message.answer("Телефон? (+7... )")

@dp.message(StateFilter(Form.phone))
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data['phone'] = message.text
    conn = sqlite3.connect('logistics.db')
    c = conn.cursor()
    c.execute("""INSERT INTO orders (client_id, title, description, budget, created_at)
                 VALUES (?, ?, ?, ?, ?)""",
               (message.from_user.id, data['title'], data['description'], data['budget'], datetime.now().isoformat()))
    order_id = c.lastrowid
    c.execute("UPDATE users SET phone=?, role=? WHERE user_id=?", (data['phone'], data['role'], message.from_user.id))
    conn.commit()
    conn.close()
    
    # Матчинг
    await match_orders(order_id, message.from_user.id)
    
    await state.clear()
    await message.answer(f"✅ Заявка #{order_id} добавлена!\nМатчи отправлены.", reply_markup=main_kb(message.from_user.id))

async def match_orders(order_id: int, client_id: int):
    conn = sqlite3.connect('logistics.db')
    c = conn.cursor()
    c.execute("SELECT supplier_id FROM users WHERE role='supplier' LIMIT 5")  # Простой матч
    suppliers = c.fetchall()
    for (sup_id,) in suppliers:
        c.execute("INSERT INTO matches (order_id, supplier_id) VALUES (?, ?)", (order_id, sup_id))
        try:
            await bot.send_message(sup_id, f"Новый матч! Заявка #{order_id} от клиента {client_id}")
        except:
            pass
    conn.commit()
    conn.close()

@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    conn = sqlite3.connect('logistics.db')
    c = conn.cursor()
    c.execute("SELECT id, title, status FROM orders WHERE client_id=?", (callback.from_user.id,))
    orders = c.fetchall()
    text = "📦 <b>Твои заявки:</b>\n" + "\n".join([f"#{o[0]} {o[1]} ({o[2]})" for o in orders]) or "Пусто."
    conn.close()
    await callback.message.edit_text(text, reply_markup=main_kb(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data.startswith("admin"))
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только админ!")
        return
    data = callback.data
    if data == "admin":
        await callback.message.edit_text("👨‍💼 <b>Админ-панель</b>", reply_markup=admin_kb())
    elif data == "all_orders":
        conn = sqlite3.connect('logistics.db')
        c = conn.cursor()
        c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20")
        orders = c.fetchall()
        text = "📋 <b>Все заявки:</b>\n" + "\n".join([f"#{o[0]} {o[1]} | {o[4]}р | {o[5]}" for o in orders]) or "Пусто."
        conn.close()
        await callback.message.edit_text(text, reply_markup=admin_kb())
    elif data == "export_csv":
        conn = sqlite3.connect('logistics.db')
        c = conn.cursor()
        c.execute("SELECT * FROM orders")
        rows = c.fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Client', 'Title', 'Desc', 'Budget', 'Status'])
        writer.writerows(rows)
        csv_content = output.getvalue()
        with open('orders.csv', 'w') as f:
            f.write(csv_content)
        await bot.send_document(callback.from_user.id, FSInputFile('orders.csv'))
    elif data == "broadcast":
        await callback.message.edit_text("Текст рассылки?")
        # Добавь FSM для рассылки
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню", reply_markup=main_kb(callback.from_user.id))

# Планировщик уведомлений
scheduler = AsyncIOScheduler()
scheduler.add_job(lambda: asyncio.create_task(bot.send_message(ADMIN_ID, "📊 Ежедневный отчёт: новые лиды!")), 'cron', hour=9)
scheduler.start()

async def main():
    init_db()
    print("🚀 Логистический бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
