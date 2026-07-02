import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from groq import Groq
import json
import os

logging.basicConfig(level=logging.INFO)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 1249820876

# Память пользователей
user_data = {}  # {user_id: {brand, history, settings, pro_expiry, free_left}}

# ==================== КЛАВИАТУРЫ ====================

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Быстрый Listing", callback_data="quick")
    builder.button(text="📋 Полный Listing", callback_data="full")
    builder.button(text="📷 По фото", callback_data="photo")
    builder.button(text="🔍 Анализ конкурента", callback_data="competitor")
    builder.button(text="💬 Ответ покупателю", callback_data="reply")
    builder.button(text="📊 Дайджест магазина", callback_data="digest")
    builder.button(text="🧠 Мой бренд", callback_data="brand")
    builder.button(text="🚀 Идеи роста", callback_data="growth")
    builder.button(text="💎 Тарифы", callback_data="pricing")
    builder.adjust(2)
    return builder.as_markup()

# ==================== ПРИВЕТСТВИЕ ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    uid = message.from_user.id
    if uid not in user_data:
        user_data[uid] = {
            "brand_name": "",
            "niche": "",
            "style": "professional_warm",
            "history": [],
            "free_left": 5,
            "is_pro": False,
            "pro_expiry": None
        }
    
    await message.answer(
        "👋 <b>Добро пожаловать в EtsyScribe AI</b>\n\n"
        "Я — твой личный AI-партнёр по продажам на всех маркетплейсах.\n\n"
        "Я помню твой бренд и помогаю каждый день.\n\n"
        "Что делаем сегодня?",
        reply_markup=main_menu()
    )

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

@dp.callback_query(F.data == "quick")
async def quick_listing(callback: types.CallbackQuery):
    await callback.message.answer("✍️ Отправь название товара — я сразу создам listing.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "full")
async def full_listing(callback: types.CallbackQuery):
    await callback.message.answer("📋 Отправь подробное описание товара (материалы, размеры, стиль).", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "photo")
async def photo_listing(callback: types.CallbackQuery):
    await callback.message.answer("📷 Отправь фото товара + название.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "competitor")
async def competitor(callback: types.CallbackQuery):
    await callback.message.answer("🔍 Отправь ссылку на listing конкурента.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "reply")
async def customer_reply(callback: types.CallbackQuery):
    await callback.message.answer("💬 Перешли мне сообщение покупателя — я напишу ответ.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "digest")
async def store_digest(callback: types.CallbackQuery):
    await callback.message.answer("📊 Анализирую твой магазин... (демо)", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "brand")
async def my_brand(callback: types.CallbackQuery):
    await callback.message.answer("🧠 Отправь информацию о своём бренде (ниша, стиль, целевая аудитория).", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "growth")
async def growth_ideas(callback: types.CallbackQuery):
    await callback.message.answer("🚀 Идеи для роста твоего магазина (демо).", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main")))

@dp.callback_query(F.data == "pricing")
async def pricing(callback: types.CallbackQuery):
    await callback.message.answer(
        "💎 <b>Тарифы</b>\n\n"
        "Free — 5 генераций\n"
        "Starter — 490₽/мес\n"
        "Pro — 1490₽/мес (Безлимит)\n"
        "Business — 2990₽/мес (Команда + API)",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("← Назад", callback_data="main"))
    )

@dp.callback_query(F.data == "main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

# ==================== ОБРАБОТКА ТЕКСТА ====================

@dp.message()
async def handle_text(message: types.Message):
    uid = message.from_user.id
    text = message.text

    await message.answer("Генерирую ответ...")

    # Здесь можно добавить вызов Groq с памятью пользователя
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}],
            temperature=0.7
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer("Ошибка. Попробуй ещё раз.")

# ==================== ЗАПУСК ====================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
