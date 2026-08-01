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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BusinessConnection
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
        CREATE TABLE IF NOT EXISTS user_connections (
            user_id INTEGER PRIMARY KEY,
            connection_id TEXT,
            connected_at TIMESTAMP
        )
    ''')
    
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
    
    conn.commit()
    conn.close()

def save_connection(user_id: int, connection_id: str):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_connections (user_id, connection_id, connected_at) VALUES (?, ?, ?)",
        (user_id, connection_id, datetime.now())
    )
    conn.commit()
    conn.close()
    logging.info(f"✅ Сохранен connection_id для user_id={user_id}")

def get_connection_id(user_id: int):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT connection_id FROM user_connections WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def delete_connection(user_id: int):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("DELETE FROM user_connections WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    logging.info(f"🗑️ Удален connection_id для user_id={user_id}")

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
    keyboard.row(InlineKeyboardButton(text="🔄 Сбросить подключение", callback_data="reset_connection"))
    return keyboard.as_markup()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 **Привет! Я MGP3 бот для отслеживания удаленных сообщений!**\n\n"
        "**Как подключить:**\n"
        "1️⃣ Нажми «Подключить к Business API»\n"
        "2️⃣ В Telegram: Профиль → Автоматизация чатов → Добавить бота\n"
        "3️⃣ Выбери этого бота и разреши доступ\n"
        "4️⃣ Нажми «Проверить подключение»\n\n"
        "⬇️ Нажми на кнопки ниже",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "instructions")
async def show_instructions(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 **Инструкция по настройке**\n\n"
        "**Шаг 1:** Нажми «Подключить к Business API»\n"
        "**Шаг 2:** В Telegram: Профиль → Автоматизация чатов → Добавить бота\n"
        "**Шаг 3:** Выбери этого бота и разреши доступ ко всем чатам\n"
        "**Шаг 4:** Нажми «Проверить подключение»\n\n"
        "⚠️ Если не работает — нажми «Сбросить подключение» и повтори шаги",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
            ]
        )
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 **Главное меню**\n\nВыбери действие:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "reset_connection")
async def reset_connection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    delete_connection(user_id)
    await callback.message.answer(
        "🔄 **Подключение сброшено!**\n\n"
        "Теперь:\n"
        "1️⃣ Удали бота из Профиль → Автоматизация чатов\n"
        "2️⃣ Снова добавь его\n"
        "3️⃣ Нажми «Проверить подключение»"
    )
    await callback.answer()

@dp.callback_query(F.data == "check_connection")
async def check_connection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    connection_id = get_connection_id(user_id)
    
    if connection_id:
        await callback.message.answer(
            f"✅ **Подключение активно!**\n\n"
            f"Connection ID: `{connection_id}`\n"
            f"Я сохраняю все сообщения из твоих чатов.",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            "❌ **Подключение не найдено**\n\n"
            "Сделай:\n"
            "1️⃣ Нажми «Сбросить подключение»\n"
            "2️⃣ В Telegram: Профиль → Автоматизация чатов → удали бота\n"
            "3️⃣ Снова добавь бота\n"
            "4️⃣ Нажми «Проверить подключение»"
        )
    await callback.answer()

# ==================== BUSINESS API ====================

@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    user_id = connection.user_id
    connection_id = connection.connection_id
    
    save_connection(user_id, connection_id)
    
    await bot.send_message(
        chat_id=user_id,
        text=(
            "🔔 **Бизнес-подключение установлено!**\n\n"
            f"Connection ID: `{connection_id}`\n"
            "Теперь я сохраняю все сообщения из твоих чатов. 🚀\n\n"
            "✅ Нажми «Проверить подключение» — должно показать активно!"
        ),
        parse_mode="Markdown"
    )
    
    logging.info(f"✅ Business connection установлен для user_id={user_id}")

@dp.message(F.business_message)
async def handle_business_message(message: types.Message):
    if not message.business_message:
        return
    
    user_id = message.from_user.id
    
    if hasattr(message, 'business_connection_id') and message.business_connection_id:
        if not get_connection_id(user_id):
            save_connection(user_id, message.business_connection_id)
    
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
    elif message.voice:
        media_type = "voice"
        media_id = message.voice.file_id
    elif message.audio:
        media_type = "audio"
        media_id = message.audio.file_id
    elif message.sticker:
        media_type = "sticker"
        media_id = message.sticker.file_id
    
    save_message(
        user_id=user_id,
        message_id=message.message_id,
        chat_id=message.chat.id,
        text=text,
        media_type=media_type,
        media_id=media_id
    )

@dp.edited_business_message()
async def handle_edited_business_message(message: types.Message):
    user_id = message.from_user.id
    
    if hasattr(message, 'business_connection_id') and message.business_connection_id:
        if not get_connection_id(user_id):
            save_connection(user_id, message.business_connection_id)
    
    old_data = get_message(user_id, message.message_id, message.chat.id)
    
    if old_data:
        old_text, old_media_type, old_media_id = old_data
        
        notification = (
            "✏️ **Сообщение было изменено!**\n\n"
            f"**Было:**\n{old_text or 'Медиафайл'}\n\n"
            f"**Стало:**\n{message.text or message.caption or 'Медиафайл'}"
        )
        
        await bot.send_message(user_id, notification)
        
        save_message(
            user_id=user_id,
            message_id=message.message_id,
            chat_id=message.chat.id,
            text=message.text or message.caption,
            media_type=old_media_type,
            media_id=old_media_id
        )

@dp.business_messages_deleted()
async def handle_deleted_business_messages(event: types.BusinessMessagesDeleted):
    user_id = event.user_id
    
    if hasattr(event, 'business_connection_id') and event.business_connection_id:
        if not get_connection_id(user_id):
            save_connection(user_id, event.business_connection_id)
    
    for msg_id in event.message_ids:
        old_data = get_message(user_id, msg_id, event.chat.id)
        
        if old_data:
            text, media_type, media_id = old_data
            
            notification = (
                "🗑️ **Сообщение было удалено!**\n\n"
                f"**Текст:**\n{text or 'Медиафайл'}"
            )
            
            await bot.send_message(user_id, notification)
            delete_message(user_id, msg_id, event.chat.id)

# ==================== ЗАПУСК ====================

async def main():
    init_db()
    logging.info("🚀 MGP3 бот запущен!")
    logging.info("💡 Подключи бота в Профиль → Автоматизация чатов")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())