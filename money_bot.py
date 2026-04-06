import asyncio
import os
print("🔍 Проверяю токен...")
TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN есть?", TOKEN[:10] + "..." if TOKEN else "НЕТ!")
if not TOKEN:
    print("ОШИБКА! Добавь BOT_TOKEN в Render")
    exit()

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("✅ БОТ РАБОТАЕТ!")

async def main():
    print("🚀 СТАРТ!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
