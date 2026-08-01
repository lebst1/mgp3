import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BusinessConnection

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

logging.basicConfig(level=logging.INFO)

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            message_id INTEGER,
            text TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(user_id, chat_id, message_id, text):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (user_id, chat_id, message_id, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, chat_id, message_id, text, datetime.now())
    )
    conn.commit()
    conn.close()
    logging.info(f"✅ Сохранено сообщение {message_id} от user {user_id}")

# ==================== БОТ ====================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 **Привет! Я MGP3 бот!**\n\n"
        "Я сохраняю все сообщения из твоих чатов.\n\n"
        "Просто отправь мне любое сообщение — я его сохраню!",
        parse_mode="Markdown"
    )

@dp.message(F.chat.type == "private")
async def save_all_messages(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    
    if message.text:
        text = message.text[:200]
    elif message.photo:
        text = "📸 Фото"
    elif message.video:
        text = "🎬 Видео"
    elif message.document:
        text = "📄 Документ"
    elif message.voice:
        text = "🎤 Голосовое"
    elif message.audio:
        text = "🎵 Аудио"
    elif message.sticker:
        text = "🏷️ Стикер"
    else:
        text = "📎 Медиафайл"
    
    save_message(user_id, chat_id, message_id, text)
    await message.reply(f"✅ Сохранено! ID: `{message_id}`", parse_mode="Markdown")

# ==================== BUSINESS API (ШАГ 1) ====================

@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    user_id = connection.user_id
    connection_id = connection.connection_id
    
    logging.info(f"🔔 BUSINESS CONNECTION! user_id={user_id}, connection_id={connection_id}")
    
    await bot.send_message(
        chat_id=user_id,
        text=(
            "🔔 **Бизнес-подключение установлено!**\n\n"
            f"Connection ID: `{connection_id}`\n"
            "Теперь я буду видеть сообщения из твоих чатов.\n\n"
            "Для проверки — отправь кому-нибудь сообщение, и я его сохраню."
        ),
        parse_mode="Markdown"
    )

# ==================== ЗАПУСК ====================

async def main():
    init_db()
    logging.info("🚀 MGP3 БОТ ЗАПУЩЕН!")
    logging.info("📌 /start - приветствие")
    logging.info("📌 Подключи бота через Профиль → Автоматизация чатов")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())