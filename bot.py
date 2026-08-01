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

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_messages (
            message_id INTEGER,
            chat_id INTEGER,
            user_id INTEGER,
            text TEXT,
            media_type TEXT,
            media_id TEXT,
            saved_at TIMESTAMP,
            PRIMARY KEY (message_id, chat_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_connections (
            user_id INTEGER PRIMARY KEY,
            connection_id TEXT,
            connected_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_connection(user_id: int, connection_id: str):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_connections (user_id, connection_id, connected_at) VALUES (?, ?, ?)",
              (user_id, connection_id, datetime.now()))
    conn.commit()
    conn.close()

def get_connection_id(user_id: int):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT connection_id FROM user_connections WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_message(user_id: int, message_id: int, chat_id: int, text: str = None, media_type: str = None, media_id: str = None):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO saved_messages (user_id, message_id, chat_id, text, media_type, media_id, saved_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, message_id, chat_id, text, media_type, media_id, datetime.now())
    )
    conn.commit()
    conn.close()

def get_message(user_id: int, message_id: int, chat_id: int):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT text, media_type, media_id FROM saved_messages WHERE user_id=? AND message_id=? AND chat_id=?", 
              (user_id, message_id, chat_id))
    result = c.fetchone()
    conn.close()
    return result

def delete_message(user_id: int, message_id: int, chat_id: int):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("DELETE FROM saved_messages WHERE user_id=? AND message_id=? AND chat_id=?", 
              (user_id, message_id, chat_id))
    conn.commit()
    conn.close()

# ==================== БОТ ====================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🤖 Скопировать юзера бота", switch_inline_query=""))
    keyboard.row(InlineKeyboardButton(text="🔗 Подключить к Business API", url="https://t.me/BotFather?start=set_business"))
    keyboard.row(InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions"))
    keyboard.row(InlineKeyboardButton(text="✅ Проверить подключение", callback_data="check_connection"))
    return keyboard.as_markup()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 **Привет! Я MGP3 бот для отслеживания удаленных сообщений!**\n\n"
        "Я сохраняю все сообщения из твоих личных чатов.\n\n"
        "⬇️ Нажми на кнопки ниже для настройки",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "instructions")
async def show_instructions(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 **Инструкция**\n\n"
        "1. Нажми «Подключить к Business API»\n"
        "2. В Telegram: Настройки → Telegram Business → Chatbots → добавь бота",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 **Главное меню**",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "check_connection")
async def check_connection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    connection_id = get_connection_id(user_id)
    if connection_id:
        await callback.message.answer("✅ **Подключение активно!**")
    else:
        await callback.message.answer("❌ **Подключение не найдено**")
    await callback.answer()

# ==================== MIDDLEWARE (ПРАВИЛЬНЫЙ) ====================

@dp.update.outer_middleware
async def business_middleware(handler, event: types.Update, data: dict):
    """
    ПРАВИЛЬНЫЙ middleware для aiogram 3.x
    Принимает 3 аргумента: handler, event, data
    """
    
    # Бизнес-подключение
    if event.business_connection:
        user_id = event.business_connection.user_id
        connection_id = event.business_connection.connection_id
        save_connection(user_id, connection_id)
        await bot.send_message(
            chat_id=user_id,
            text="🔔 **Бизнес-подключение установлено!** 🚀"
        )
        return
    
    # Измененные сообщения
    if event.edited_business_message:
        message = event.edited_business_message
        user_id = message.from_user.id
        old_data = get_message(user_id, message.message_id, message.chat.id)
        if old_data:
            old_text, _, _ = old_data
            await bot.send_message(
                user_id,
                f"✏️ **Сообщение изменено!**\n\nБыло: {old_text or 'Медиа'}\nСтало: {message.text or message.caption or 'Медиа'}"
            )
            save_message(user_id, message.message_id, message.chat.id, message.text or message.caption)
        return
    
    # Удаленные сообщения
    if event.business_messages_deleted:
        ev = event.business_messages_deleted
        user_id = ev.user_id
        chat_id = ev.chat.id
        for msg_id in ev.message_ids:
            old_data = get_message(user_id, msg_id, chat_id)
            if old_data:
                text, _, _ = old_data
                await bot.send_message(
                    user_id,
                    f"🗑️ **Сообщение удалено!**\n\nТекст: {text or 'Медиа'}"
                )
                delete_message(user_id, msg_id, chat_id)
        return
    
    # Передаем дальше
    return await handler(event, data)

# Новые бизнес-сообщения
@dp.message(F.business_message)
async def handle_business_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text or message.caption
    
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
    
    save_message(user_id, message.message_id, message.chat.id, text, media_type, media_id)

# ==================== ЗАПУСК ====================

async def main():
    init_db()
    logging.info("🚀 MGP3 бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())