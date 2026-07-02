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
from collections import defaultdict

logging.basicConfig(level=logging.INFO)

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 1249820876

# ==================== БАЗА ДАННЫХ ====================
user_data = defaultdict(lambda: {
    "brand_name": "Мой магазин",
    "niche": "",
    "style": "professional_warm",
    "history": [],
    "free_left": 5,
    "is_pro": False,
    "pro_expiry": None,
    "settings": {
        "model": "smart",
        "tone": "auto",
        "length": "auto",
        "seo": True
    },
    "last_activity": datetime.now(),
    "total_listings": 0,
    "successful_sales": 0
})

# ==================== КРАСИВЫЕ КЛАВИАТУРЫ ====================

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Быстрый Listing", callback_data="quick_listing")
    builder.button(text="📋 Полный Listing", callback_data="full_listing")
    builder.button(text="📷 По фото", callback_data="photo_listing")
    builder.button(text="🔍 Анализ конкурента", callback_data="competitor_analysis")
    builder.button(text="💬 Ответ покупателю", callback_data="customer_reply")
    builder.button(text="📊 Дайджест магазина", callback_data="store_digest")
    builder.button(text="🧠 Мой бренд", callback_data="my_brand")
    builder.button(text="🚀 Идеи роста", callback_data="growth_ideas")
    builder.button(text="💎 Тарифы", callback_data="pricing")
    builder.button(text="📜 История", callback_data="history")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def back_button():
    builder = InlineKeyboardBuilder()
    builder.button(text="← Главное меню", callback_data="main_menu")
    return builder.as_markup()

# ==================== ПРИВЕТСТВИЕ ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    uid = message.from_user.id
    user_data[uid]["last_activity"] = datetime.now()
    
    await message.answer(
        "👋 <b>Добро пожаловать в EtsyScribe AI</b>\n\n"
        "Я — твой личный AI-партнёр по продажам.\n"
        "Я помню твой бренд и помогаю каждый день.\n\n"
        "Что делаем сегодня?",
        reply_markup=main_menu()
    )

# ==================== МЕНЮ ====================

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

@dp.callback_query(F.data == "quick_listing")
async def quick_listing(callback: types.CallbackQuery):
    await callback.message.answer("✍️ Отправь название товара — я сразу создам listing.", reply_markup=back_button())

@dp.callback_query(F.data == "full_listing")
async def full_listing(callback: types.CallbackQuery):
    await callback.message.answer("📋 Отправь подробное описание товара.", reply_markup=back_button())

@dp.callback_query(F.data == "photo_listing")
async def photo_listing(callback: types.CallbackQuery):
    await callback.message.answer("📷 Отправь фото товара + название.", reply_markup=back_button())

@dp.callback_query(F.data == "competitor_analysis")
async def competitor_analysis(callback: types.CallbackQuery):
    await callback.message.answer("🔍 Отправь ссылку на listing конкурента.", reply_markup=back_button())

@dp.callback_query(F.data == "customer_reply")
async def customer_reply(callback: types.CallbackQuery):
    await callback.message.answer("💬 Перешли мне сообщение покупателя.", reply_markup=back_button())

@dp.callback_query(F.data == "store_digest")
async def store_digest(callback: types.CallbackQuery):
    await callback.message.answer("📊 Генерирую дайджест...", reply_markup=back_button())

@dp.callback_query(F.data == "my_brand")
async def my_brand(callback: types.CallbackQuery):
    await callback.message.answer("🧠 Отправь информацию о своём бренде.", reply_markup=back_button())

@dp.callback_query(F.data == "growth_ideas")
async def growth_ideas(callback: types.CallbackQuery):
    await callback.message.answer("🚀 Вот идеи для роста твоего магазина...", reply_markup=back_button())

@dp.callback_query(F.data == "pricing")
async def pricing(callback: types.CallbackQuery):
    await callback.message.answer(
        "💎 <b>Тарифы EtsyScribe AI</b>\n\n"
        "Free — 5 генераций\n"
        "Starter — 490₽/мес\n"
        "Pro — 1490₽/мес (Безлимит + память бренда)\n"
        "Business — 2990₽/мес (Команда + API)",
        reply_markup=back_button()
    )

@dp.callback_query(F.data == "history")
async def history(callback: types.CallbackQuery):
    await callback.message.answer("📜 История твоих listings (демо).", reply_markup=back_button())

@dp.callback_query(F.data == "settings")
async def settings(callback: types.CallbackQuery):
    await callback.message.answer("⚙️ Настройки (демо).", reply_markup=back_button())

# ==================== ОБРАБОТКА ТЕКСТА ====================

@dp.message()
async def handle_text(message: types.Message):
    uid = message.from_user.id
    text = message.text

    await message.answer("🤖 Думаю...")

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
    print("🚀 EtsyScribe AI запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
