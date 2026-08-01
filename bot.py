import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

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

def get_all_messages(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT message_id, text, created_at FROM messages WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))
    result = c.fetchall()
    conn.close()
    return result

# ==================== БОТ ====================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- КОМАНДЫ ----------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 **Привет! Я MGP3 бот!**\n\n"
        "Я сохраняю все сообщения из твоих чатов.\n\n"
        "📌 **Команды:**\n"
        "/start - показать это сообщение\n"
        "/stats - показать статистику\n"
        "/last - показать последние 10 сохраненных сообщений\n\n"
        "Просто отправь мне любое сообщение — я его сохраню!",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def stats(message: types.Message):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE user_id=?", (message.from_user.id,))
    count = c.fetchone()[0]
    conn.close()
    await message.answer(f"📊 **Статистика:**\n\nСохранено сообщений: {count}", parse_mode="Markdown")

@dp.message(Command("last"))
async def last_messages(message: types.Message):
    messages = get_all_messages(message.from_user.id)
    if not messages:
        await message.answer("❌ У тебя пока нет сохраненных сообщений.")
        return
    
    text = "📋 **Последние 10 сообщений:**\n\n"
    for msg_id, msg_text, created_at in messages:
        created = created_at[:16] if created_at else "неизвестно"
        text += f"🆔 `{msg_id}` | {created}\n📝 {msg_text[:50]}...\n\n"
    
    await message.answer(text, parse_mode="Markdown")

# ---------- СОХРАНЕНИЕ ВСЕХ СООБЩЕНИЙ ----------

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

# ==================== ЗАПУСК ====================

async def main():
    init_db()
    logging.info("🚀 MGP3 БОТ ЗАПУЩЕН НА BOTHOST!")
    logging.info("📌 Команды: /start, /stats, /last")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())