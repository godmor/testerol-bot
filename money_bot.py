import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage   # ← добавить эту строку!

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить задачи", callback_data="run")],
        [InlineKeyboardButton(text="📊 Мои лиды", callback_data="my_leads")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")]
    ])
    await message.answer("💰 MoneyLogiBot готов!\nВыбери действие:", reply_markup=kb)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = (
        "🚀 Доступные команды:\n"
        "/start — главное меню\n"
        "/help — этот текст\n"
        "/leads — показать лиды\n"
        "/info — информация о боте"
    )
    await message.answer(text)

@dp.message(Command("leads"))
async def leads_cmd(message: types.Message):
    text = (
        "📊 Найденные лиды:\n"
        "• +7(900)123-45-67 (ЕКБ, курьер)\n"
        "• +7(912)765-43-21 (ЕКБ, поставщик)"
    )
    await message.answer(text)

@dp.message(Command("info"))
async def info_cmd(message: types.Message):
    await message.answer("💰 MoneyLogiBot — тестовый бот для логистики. Тестовый.")

@dp.callback_query(F.data == "run")
async def run_tasks(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "✅ Задачи выполнены!\n📊 Найдено 2 лида:\n"
        "• +7(900)123-45-67 (ЕКБ, курьер)\n"
        "• +7(912)765-43-21 (ЕКБ, поставщик)"
    )
    await callback.answer("Готово!")

@dp.callback_query(F.data == "my_leads")
async def my_leads(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📊 Обнаруженные лиды системой:\n\n"
        "1. Курьер из ЕКБ: +7(900)123-45-67\n"
        "2. Поставщик в ЕКБ: +7(912)765-43-21"
    )
    await callback.answer("Лиды загружены.")

@dp.callback_query(F.data == "about")
async def about_bot(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ MoneyLogiBot\n"
        "— Тестовый бот для моделирования логистических задач.\n"
        "— Функции: создание и учёт лидов."
    )
    await callback.answer("О боте")

@dp.message()
async def handle_any_message(message: types.Message):
    text = (
        "Я пока не понимаю этот запрос.\n"
        "Введите /start или /help."
    )
    await message.answer(text)

async def main():
    print("🚀 Бот запущен! Тестируй в Telegram.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
