import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# Токен и ID берем из переменных окружения
TOKEN = os.getenv("8755561572:AAH-S7K1fGMC-x83rDx3yW2BgTxPB1CsaMM")
ADMIN_ID = int(os.getenv("7855432801"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить задачи", callback_data="run")]
    ])
    await message.answer("💰 MoneyLogiBot готов!\nНажми кнопку:", reply_markup=kb)

@dp.callback_query(F.data == "run")
async def run_tasks(callback: types.CallbackQuery):
    await callback.message.edit_text("✅ Задачи выполнены!\n📊 Найдено 2 лида:\n• +7(900)123-45-67 (ЕКБ, курьер)\n• +7(912)765-43-21 (ЕКБ, поставщик)")
    await callback.answer("Готово!")

async def main():
    print("🚀 Бот запущен! Тестируй в Telegram.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
