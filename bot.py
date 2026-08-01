import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🤖 Скопировать юзера бота", switch_inline_query=""))
    keyboard.row(InlineKeyboardButton(text="🔗 Подключить к Business API", url="https://t.me/BotFather?start=set_business"))
    keyboard.row(InlineKeyboardButton(text="📖 Инструкция по настройке", callback_data="instructions"))
    keyboard.row(InlineKeyboardButton(text="✅ Проверить подключение", callback_data="check_connection"))
    return keyboard.as_markup()

@dp.message(Command("start"))
async def start(message: types.Message):
    welcome_text = (
        "👋 **Привет! Я MGP3 бот для отслеживания удаленных сообщений!**\n\n"
        "Я сохраняю все сообщения из твоих личных чатов, и если собеседник "
        "удалит или изменит сообщение — я пришлю тебе его оригинальный текст.\n\n"
        "**Как меня настроить:**\n"
        "1️⃣ Нажми кнопку ниже «Подключить к Business API»\n"
        "2️⃣ Выбери свой аккаунт и разреши доступ\n"
        "3️⃣ Я автоматически начну сохранять сообщения\n\n"
        "**Что я умею:**\n"
        "✅ Сохранять текст сообщений\n"
        "✅ Сохранять фото и видео\n"
        "✅ Отслеживать удаление сообщений\n"
        "✅ Отслеживать изменение сообщений\n"
        "✅ Отправлять уведомления тебе в ЛС\n\n"
        "⬇️ Нажми на кнопки ниже для настройки"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "instructions")
async def show_instructions(callback: types.CallbackQuery):
    instructions = (
        "📖 **Подробная инструкция по настройке**\n\n"
        "**Шаг 1:** Нажми «Подключить к Business API»\n"
        "**Шаг 2:** В Telegram: Настройки → Telegram Business → Chatbots → добавь бота\n"
        "**Шаг 3:** Нажми «Проверить подключение»\n\n"
        "⚠️ Бот сохраняет сообщения ТОЛЬКО после подключения."
    )
    await callback.message.edit_text(
        instructions,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
        ])
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

@dp.callback_query(F.data == "check_connection")
async def check_connection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    connection_id = get_connection_id(user_id)
    if connection_id:
        await callback.message.answer("✅ **Подключение активно!**")
    else:
        await callback.message.answer("❌ **Подключение не найдено**")
    await callback.answer()

# Используем types.BusinessConnection вместо прямого импорта
@dp.business_connection()
async def on_business_connection(connection: types.BusinessConnection):
    user_id = connection.user_id
    save_connection(user_id, connection.connection_id)
    await bot.send_message(chat_id=user_id, text="🔔 **Бизнес-подключение установлено!**")

@dp.business_message()
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
    elif message.voice:
        media_type = "voice"
        media_id = message.voice.file_id
    elif message.audio:
        media_type = "audio"
        media_id = message.audio.file_id
    save_message(user_id, message.message_id, message.chat.id, text, media_type, media_id)

@dp.edited_business_message()
async def handle_edited_business_message(message: types.Message):
    user_id = message.from_user.id
    old_data = get_message(user_id, message.message_id, message.chat.id)
    if old_data:
        old_text, _, _ = old_data
        notification = (
            "✏️ **Сообщение изменено!**\n\n"
            f"**Было:** {old_text or 'Медиа'}\n\n"
            f"**Стало:** {message.text or message.caption or 'Медиа'}"
        )
        await bot.send_message(user_id, notification)
        save_message(user_id, message.message_id, message.chat.id, message.text or message.caption)

@dp.business_messages_deleted()
async def handle_deleted_business_messages(event: types.BusinessMessagesDeleted):
    user_id = event.user_id
    chat_id = event.chat.id
    for msg_id in event.message_ids:
        old_data = get_message(user_id, msg_id, chat_id)
        if old_data:
            text, media_type, media_id = old_data
            notification = f"🗑️ **Сообщение удалено!**\n\nТекст: {text or 'Медиа'}"
            if media_id:
                try:
                    if media_type == "photo":
                        await bot.send_photo(user_id, media_id, caption=text)
                    elif media_type == "video":
                        await bot.send_video(user_id, media_id, caption=text)
                    elif media_type == "document":
                        await bot.send_document(user_id, media_id, caption=text)
                    elif media_type == "voice":
                        await bot.send_voice(user_id, media_id, caption=text)
                    elif media_type == "audio":
                        await bot.send_audio(user_id, media_id, caption=text)
                    else:
                        await bot.send_message(user_id, notification)
                except:
                    await bot.send_message(user_id, notification)
            else:
                await bot.send_message(user_id, notification)
            delete_message(user_id, msg_id, chat_id)

async def main():
    init_db()
    logging.info("🚀 MGP3 бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())