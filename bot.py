import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

import aiogram
print(f"✅ aiogram version: {aiogram.__version__}")

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS saved_messages (
        message_id INTEGER, chat_id INTEGER, user_id INTEGER,
        text TEXT, media_type TEXT, media_id TEXT, saved_at TIMESTAMP,
        PRIMARY KEY (message_id, chat_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_connections (
        user_id INTEGER PRIMARY KEY, connection_id TEXT, connected_at TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_connection(user_id, connection_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_connections VALUES (?, ?, ?)",
              (user_id, connection_id, datetime.now()))
    conn.commit()
    conn.close()

def get_connection_id(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT connection_id FROM user_connections WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_message(user_id, message_id, chat_id, text=None, media_type=None, media_id=None):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO saved_messages VALUES (?, ?, ?, ?, ?, ?, ?)",
              (message_id, chat_id, user_id, text, media_type, media_id, datetime.now()))
    conn.commit()
    conn.close()

def get_message(user_id, message_id, chat_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT text, media_type, media_id FROM saved_messages WHERE user_id=? AND message_id=? AND chat_id=?", 
              (user_id, message_id, chat_id))
    result = c.fetchone()
    conn.close()
    return result

def delete_message(user_id, message_id, chat_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("DELETE FROM saved_messages WHERE user_id=? AND message_id=? AND chat_id=?", 
              (user_id, message_id, chat_id))
    conn.commit()
    conn.close()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🤖 Скопировать юзера", switch_inline_query=""))
    keyboard.row(InlineKeyboardButton(text="🔗 Подключить Business API", url="https://t.me/BotFather?start=set_business"))
    keyboard.row(InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions"))
    keyboard.row(InlineKeyboardButton(text="✅ Проверить", callback_data="check_connection"))
    return keyboard.as_markup()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет! Отслеживаю удаленные сообщения.", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "instructions")
async def instructions(callback: types.CallbackQuery):
    await callback.message.edit_text("📖 Инструкция: подключи бота через Business API", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]))
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Главное меню", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "check_connection")
async def check(callback: types.CallbackQuery):
    if get_connection_id(callback.from_user.id):
        await callback.message.answer("✅ Подключено!")
    else:
        await callback.message.answer("❌ Не подключено")
    await callback.answer()

# ========== ВСЯ БИЗНЕС-ЛОГИКА В ОДНОМ MIDDLEWARE ==========
@dp.update.outer_middleware
async def business_handler(update: types.Update, handler):
    # Подключение
    if update.business_connection:
        save_connection(update.business_connection.user_id, update.business_connection.connection_id)
        await bot.send_message(update.business_connection.user_id, "🔔 Бизнес-подключение установлено!")
        return
    
    # Изменение
    if update.edited_business_message:
        msg = update.edited_business_message
        old = get_message(msg.from_user.id, msg.message_id, msg.chat.id)
        if old:
            await bot.send_message(msg.from_user.id, f"✏️ Изменено!\nБыло: {old[0]}\nСтало: {msg.text}")
            save_message(msg.from_user.id, msg.message_id, msg.chat.id, msg.text)
        return
    
    # Удаление
    if update.business_messages_deleted:
        for msg_id in update.business_messages_deleted.message_ids:
            old = get_message(update.business_messages_deleted.user_id, msg_id, update.business_messages_deleted.chat.id)
            if old:
                await bot.send_message(update.business_messages_deleted.user_id, f"🗑️ Удалено!\nТекст: {old[0]}")
                delete_message(update.business_messages_deleted.user_id, msg_id, update.business_messages_deleted.chat.id)
        return
    
    return await handler(update)

# Новые сообщения
@dp.message(F.business_message)
async def new_business_message(message: types.Message):
    media_type = None
    media_id = None
    if message.photo:
        media_type = "photo"
        media_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_id = message.video.file_id
    elif message.document:
        media_type = "document"
        media_id = message.document.file_id
    save_message(message.from_user.id, message.message_id, message.chat.id, 
                message.text or message.caption, media_type, media_id)

async def main():
    init_db()
    logging.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())