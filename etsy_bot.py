import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
import re
import os
import base64
from datetime import datetime, timedelta
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
USDT_ADDRESS = os.environ.get("USDT_ADDRESS", "YOUR_USDT_TRC20_ADDRESS")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 1249820876
OWNER_USERNAME = "sunafery"
BOT_USERNAME = "REPLACE_WITH_YOUR_BOT_USERNAME"
FREE_LIMIT = 3

STARS_MONTHLY = 300
STARS_6MONTH = 1500
STARS_YEARLY = 2500

user_free_left = {}
user_history = {}
pro_users = {}
user_settings = {}
user_text_history = {}
referred_by = {}
all_users = set()
REFERRAL_BONUS = 2

MODELS = {
    "smart": "llama-3.3-70b-versatile",
    "fast": "llama-3.1-8b-instant"
}
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

WELCOME_TEXT = (
    "✨ Welcome to EtsyScribe — your AI listing writer for Etsy.\n\n"
    "I write SEO-optimized, emotionally compelling product descriptions "
    "that help your Etsy shop stand out and sell faster.\n\n"
    "What I do:\n"
    "🖋 Write handmade, vintage & digital product listings\n"
    "🔍 Add SEO keywords that rank in Etsy search\n"
    "📷 Recognize your item from a photo\n"
    "✏️ Rewrite, shorten or edit right in chat\n"
    "🏷️ Generate tags and titles optimized for Etsy\n\n"
    "How to start: just send me your item name and a few details.\n"
    "Example: Handmade ceramic mug, sage green, 12oz, botanical leaf pattern\n\n"
    "🎁 You have 3 free listings to try. No sign-up needed."
)

MENU_MAIN_TEXT = "📋 Main menu\n\nPick a section or just send your item details:"
MENU_ABOUT_TEXT = (
    "✨ About EtsyScribe\n\n"
    "EtsyScribe was built for Etsy sellers who want listings that actually convert — "
    "not just descriptions, but stories that make buyers feel something.\n\n"
    "I understand handmade, vintage and digital products deeply. "
    "I know how Etsy search works, what keywords drive traffic, "
    "and how to write titles and tags that rank.\n\n"
    "What makes me different:\n"
    "🔍 SEO-first: every listing is optimized for Etsy search\n"
    "💬 Tone-aware: I match your shop voice — warm, minimal, boho, luxury\n"
    "⚡ Fast: 10 seconds vs. 20 minutes of staring at a blank screen\n"
    "📷 Photo-smart: send a photo and I'll figure out the item myself\n\n"
    "Used by Etsy sellers in the US, UK, Canada and Australia."
)
MENU_SUPPORT_TEXT = (
    "🛠️ Support\n\n"
    "Something not working, or have a feature idea?\n"
    "Tap below — I reply fast and actually read every message."
)

SETTINGS_MAIN_TEXT = "⚙️ Settings\n\nCustomize how I write your listings:"

def get_sub_text():
    return (
        "💎 Subscription Plans\n\n"
        "Unlimited listings, priority support, and full access to all features.\n\n"
        "Choose your plan:\n\n"
        "🗓 Monthly — 300 ⭐ (~$3.99)\n"
        "Best for trying it out\n\n"
        "📅 6 Months — 1500 ⭐ (~$17.99)\n"
        "Save 25% vs monthly\n\n"
        "🏆 Yearly — 2500 ⭐ (~$29.99)\n"
        "Best value — save 37%\n\n"
        "Pay with Telegram Stars (instant, automatic activation)\n"
        "or USDT (TRC-20) — send to:\n"
        "`" + USDT_ADDRESS + "`\n\n"
        "After USDT payment: send screenshot + /myid to support."
    )

def get_settings(uid):
    if uid not in user_settings:
        user_settings[uid] = {"model": "smart", "tone": "auto", "length": "auto", "seo": True}
    return user_settings[uid]

def clean_text(text):
    return re.sub(r'[\u3040-\u30ff\uac00-\ud7af\u4e00-\u9fff]', '', text)

def is_unlimited(uid):
    if uid == OWNER_ID:
        return True
    expiry = pro_users.get(uid)
    return expiry is not None and expiry > datetime.now()

def get_free_left(uid):
    if uid not in user_free_left:
        user_free_left[uid] = FREE_LIMIT
    return user_free_left[uid]

def add_to_text_history(uid, text):
    if uid not in user_text_history:
        user_text_history[uid] = []
    user_text_history[uid].append(text)
    if len(user_text_history[uid]) > 5:
        user_text_history[uid].pop(0)

def build_system_prompt(settings_):
    tone_pref = settings_.get("tone", "auto")
    length_pref = settings_.get("length", "auto")
    seo = settings_.get("seo", True)

    tone_line = ""
    if tone_pref == "warm":
        tone_line = "Use a warm, personal, storytelling tone — like a maker talking about their craft."
    elif tone_pref == "minimal":
        tone_line = "Use a clean, minimal, modern tone — concise and elegant."
    elif tone_pref == "luxury":
        tone_line = "Use a luxury, elevated tone — sophisticated vocabulary, aspirational feel."
    elif tone_pref == "boho":
        tone_line = "Use a boho, earthy, free-spirited tone — natural materials, artisan feel."

    length_line = ""
    if length_pref == "short":
        length_line = "Keep listings concise — 3-5 sentences max."
    elif length_pref == "long":
        length_line = "Write detailed, thorough listings — 8-12 sentences."

    seo_line = ""
    if seo:
        seo_line = ("Always include an SEO-optimized title (max 140 chars) and 13 relevant Etsy tags "
                   "as a comma-separated list at the end. "
                   "Research-backed Etsy SEO: use long-tail keywords, include material, occasion, style, color.")

    return (
        "You are EtsyScribe, an expert AI listing writer for Etsy. "
        "You specialize in handmade items, vintage goods, and digital products. "
        "You understand Etsy's search algorithm deeply.\n\n"
        "Your listing structure:\n"
        "1. TITLE: SEO-optimized, 130-140 characters, front-load the most important keywords\n"
        "2. DESCRIPTION: Emotional hook first sentence. Then: what it is, materials, dimensions if given, "
        "care instructions if relevant, who it's perfect for, why it makes a great gift. "
        "Write like a human maker, not a robot.\n"
        "3. TAGS: 13 comma-separated Etsy tags (2-3 word phrases, mix broad and specific)\n\n"
        "Etsy-specific rules:\n"
        "- If the item is a known brand or style, use your knowledge of it\n"
        "- If user's message explicitly names a brand/style/material, trust that completely\n"
        "- Do not invent facts you don't know — write warmly but honestly\n"
        "- Understand Etsy categories: handmade (jewelry, clothing, home decor, art), "
        "vintage (20+ years old items), digital downloads (printables, templates, SVG files)\n"
        "- Use buyer-focused language: 'perfect for', 'makes a thoughtful gift', 'you'll love'\n"
        "- Do not use ALL CAPS or excessive exclamation marks\n"
        + tone_line + " " + length_line + "\n"
        + seo_line + "\n\n"
        "General rules:\n"
        "- Always respond in English\n"
        "- Use conversation context when asked to rewrite or edit\n"
        "- Don't add template phrases offering to rewrite unless asked\n"
        "- Be natural and helpful like a real Etsy expert friend"
    )

def get_user_state(uid):
    if uid not in user_history:
        user_history[uid] = []
    return user_history[uid]

def build_main_menu_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✨ About EtsyScribe", callback_data="menu_about"),
        InlineKeyboardButton("💎 Subscription Plans", callback_data="menu_subscription"),
        InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        InlineKeyboardButton("🛠️ Support", callback_data="menu_support")
    )
    return markup

def build_about_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_main"))
    return markup

def build_support_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✉️ Contact support", url="https://t.me/" + OWNER_USERNAME))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_main"))
    return markup

def build_sub_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🗓 Monthly — 300 ⭐", callback_data="pay_monthly"),
        InlineKeyboardButton("📅 6 Months — 1500 ⭐ (save 25%)", callback_data="pay_6month"),
        InlineKeyboardButton("🏆 Yearly — 2500 ⭐ (save 37%)", callback_data="pay_yearly"),
        InlineKeyboardButton("💰 Pay with USDT (crypto)", callback_data="pay_usdt"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu_main")
    )
    return markup

def build_settings_main_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🤖 AI Model  >", callback_data="set_open_model"),
        InlineKeyboardButton("🎨 Tone & Style  >", callback_data="set_open_tone"),
        InlineKeyboardButton("📄 Listing Length  >", callback_data="set_open_length"),
        InlineKeyboardButton("🔄 Reset to defaults", callback_data="set_reset"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu_main")
    )
    return markup

def build_model_markup(s):
    options = [("smart", "Smart — more accurate & detailed"), ("fast", "⚡ Fast — instant responses")]
    options.sort(key=lambda x: 0 if x[0] == s["model"] else 1)
    markup = InlineKeyboardMarkup(row_width=1)
    for key, label in options:
        prefix = "✅ " if s["model"] == key else ""
        markup.add(InlineKeyboardButton(prefix + label, callback_data="set_model_" + key))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_tone_markup(s):
    options = [
        ("auto", "🤖 Automatic"),
        ("warm", "🌿 Warm & Storytelling"),
        ("minimal", "✦ Clean & Minimal"),
        ("luxury", "💎 Luxury & Elevated"),
        ("boho", "🌸 Boho & Earthy")
    ]
    options.sort(key=lambda x: 0 if x[0] == s["tone"] else 1)
    markup = InlineKeyboardMarkup(row_width=1)
    for key, label in options:
        prefix = "✅ " if s["tone"] == key else ""
        markup.add(InlineKeyboardButton(prefix + label, callback_data="set_tone_" + key))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_length_markup(s):
    options = [
        ("auto", "🤖 Automatic"),
        ("short", "📌 Short & Punchy (3-5 sentences)"),
        ("long", "📝 Detailed & Full (8-12 sentences)")
    ]
    options.sort(key=lambda x: 0 if x[0] == s["length"] else 1)
    markup = InlineKeyboardMarkup(row_width=1)
    for key, label in options:
        prefix = "✅ " if s["length"] == key else ""
        markup.add(InlineKeyboardButton(prefix + label, callback_data="set_length_" + key))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

DEFAULT_COMMANDS = [
    BotCommand("start", "Start / Welcome"),
    BotCommand("menu", "Main menu"),
    BotCommand("new", "New listing"),
    BotCommand("balance", "Check remaining requests"),
    BotCommand("settings", "Settings"),
    BotCommand("history", "Recent listings"),
    BotCommand("referral", "Invite a friend"),
    BotCommand("subscription", "Subscription plans"),
    BotCommand("support", "Support"),
    BotCommand("myid", "My Telegram ID")
]

OWNER_COMMANDS = DEFAULT_COMMANDS + [
    BotCommand("activate", "Grant subscription"),
    BotCommand("deactivate", "Revoke subscription"),
    BotCommand("stats", "Bot stats")
]

try:
    bot.set_my_commands(commands=DEFAULT_COMMANDS, scope=BotCommandScopeDefault())
    bot.set_my_commands(commands=OWNER_COMMANDS, scope=BotCommandScopeChat(OWNER_ID))
except Exception:
    pass

def safe_edit(call, text, markup):
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user_history[uid] = []
    all_users.add(uid)

    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_") and uid not in referred_by:
        try:
            referrer_id = int(parts[1].replace("ref_", ""))
            if referrer_id != uid:
                referred_by[uid] = referrer_id
                user_free_left[referrer_id] = user_free_left.get(referrer_id, FREE_LIMIT) + REFERRAL_BONUS
                try:
                    bot.send_message(referrer_id, "🎉 Someone joined through your link! You got +" + str(REFERRAL_BONUS) + " free listings.")
                except Exception:
                    pass
        except ValueError:
            pass

    if uid == OWNER_ID:
        bot.reply_to(message, "Hey creator! Unlimited access active. /activate, /deactivate, /stats available.")
        return

    if uid not in user_free_left:
        user_free_left[uid] = FREE_LIMIT

    bot.reply_to(message, WELCOME_TEXT)
    bot.send_message(message.chat.id, MENU_MAIN_TEXT, reply_markup=build_main_menu_markup())

@bot.message_handler(commands=['menu'])
def menu_command(message):
    bot.reply_to(message, MENU_MAIN_TEXT, reply_markup=build_main_menu_markup())

@bot.message_handler(commands=['balance'])
def balance_command(message):
    uid = message.from_user.id
    if is_unlimited(uid):
        expiry = pro_users.get(uid)
        if expiry:
            bot.reply_to(message, "💎 You have an active subscription — unlimited listings until " + expiry.strftime("%m/%d/%Y") + ".")
        else:
            bot.reply_to(message, "💎 You have unlimited access.")
    else:
        left = get_free_left(uid)
        bot.reply_to(message, "🎁 Free listings remaining: " + str(left) + " of " + str(FREE_LIMIT) + "\n\nGet unlimited with /subscription.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def main_menu_callback(call):
    uid = call.from_user.id
    action = call.data.replace("menu_", "")
    bot.answer_callback_query(call.id)
    if action == "main":
        safe_edit(call, MENU_MAIN_TEXT, build_main_menu_markup())
    elif action == "about":
        safe_edit(call, MENU_ABOUT_TEXT, build_about_markup())
    elif action == "support":
        safe_edit(call, MENU_SUPPORT_TEXT, build_support_markup())
    elif action == "subscription":
        safe_edit(call, get_sub_text(), build_sub_markup())
    elif action == "settings":
        safe_edit(call, SETTINGS_MAIN_TEXT, build_settings_main_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_open_") or call.data == "set_reset")
def settings_open_callback(call):
    uid = call.from_user.id
    s = get_settings(uid)
    bot.answer_callback_query(call.id)
    if call.data == "set_reset":
        user_settings[uid] = {"model": "smart", "tone": "auto", "length": "auto", "seo": True}
        safe_edit(call, SETTINGS_MAIN_TEXT, build_settings_main_markup())
        return
    section = call.data.replace("set_open_", "")
    if section == "model":
        safe_edit(call, "🤖 Choose AI model", build_model_markup(s))
    elif section == "tone":
        safe_edit(call, "🎨 Choose tone & style", build_tone_markup(s))
    elif section == "length":
        safe_edit(call, "📄 Choose listing length", build_length_markup(s))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_model_") or call.data.startswith("set_tone_") or call.data.startswith("set_length_"))
def settings_value_callback(call):
    uid = call.from_user.id
    s = get_settings(uid)
    data = call.data
    if data.startswith("set_model_"):
        s["model"] = data.replace("set_model_", "")
        bot.answer_callback_query(call.id, "Updated!")
        safe_edit(call, "🤖 Choose AI model", build_model_markup(s))
    elif data.startswith("set_tone_"):
        s["tone"] = data.replace("set_tone_", "")
        bot.answer_callback_query(call.id, "Updated!")
        safe_edit(call, "🎨 Choose tone & style", build_tone_markup(s))
    elif data.startswith("set_length_"):
        s["length"] = data.replace("set_length_", "")
        bot.answer_callback_query(call.id, "Updated!")
        safe_edit(call, "📄 Choose listing length", build_length_markup(s))

@bot.callback_query_handler(func=lambda call: call.data in ["pay_monthly", "pay_6month", "pay_yearly", "pay_usdt"])
def payment_callback(call):
    bot.answer_callback_query(call.id)
    if call.data == "pay_monthly":
        prices = [LabeledPrice(label="EtsyScribe — 1 month", amount=STARS_MONTHLY)]
        bot.send_invoice(call.message.chat.id, title="EtsyScribe Monthly", description="Unlimited Etsy listings for 1 month", invoice_payload="sub_monthly", provider_token="", currency="XTR", prices=prices)
    elif call.data == "pay_6month":
        prices = [LabeledPrice(label="EtsyScribe — 6 months", amount=STARS_6MONTH)]
        bot.send_invoice(call.message.chat.id, title="EtsyScribe 6 Months", description="Unlimited Etsy listings for 6 months (save 25%)", invoice_payload="sub_6month", provider_token="", currency="XTR", prices=prices)
    elif call.data == "pay_yearly":
        prices = [LabeledPrice(label="EtsyScribe — 1 year", amount=STARS_YEARLY)]
        bot.send_invoice(call.message.chat.id, title="EtsyScribe Yearly", description="Unlimited Etsy listings for 1 year (save 37%)", invoice_payload="sub_yearly", provider_token="", currency="XTR", prices=prices)
    elif call.data == "pay_usdt":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✉️ Contact to confirm payment", url="https://t.me/" + OWNER_USERNAME))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_subscription"))
        bot.send_message(call.message.chat.id,
            "💰 Pay with USDT (TRC-20)\n\n"
            "Send USDT to this address:\n"
            "`" + USDT_ADDRESS + "`\n\n"
            "Rates:\n"
            "Monthly: $3.99 USDT\n"
            "6 Months: $17.99 USDT\n"
            "Yearly: $29.99 USDT\n\n"
            "After sending: tap the button below, send your transaction screenshot + /myid. "
            "I'll activate within 1 hour.", reply_markup=markup)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if payload == "sub_monthly":
        days = 30
    elif payload == "sub_6month":
        days = 180
    elif payload == "sub_yearly":
        days = 365
    else:
        days = 30
    expiry = datetime.now() + timedelta(days=days)
    pro_users[uid] = expiry
    duration = "1 month" if days == 30 else ("6 months" if days == 180 else "1 year")
    bot.reply_to(message, "✅ Payment confirmed! Your " + duration + " subscription is active until " + expiry.strftime("%m/%d/%Y") + ". Happy selling! ✨")

@bot.message_handler(commands=['new'])
def new_topic(message):
    uid = message.from_user.id
    user_history[uid] = []
    bot.reply_to(message, "🔄 Fresh start! Previous listing cleared.\n\nSend your new item name and details to begin.")

@bot.message_handler(commands=['support'])
def support_command(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✉️ Contact support", url="https://t.me/" + OWNER_USERNAME))
    bot.reply_to(message, MENU_SUPPORT_TEXT, reply_markup=markup)

@bot.message_handler(commands=['referral'])
def referral_command(message):
    uid = message.from_user.id
    link = "https://t.me/" + BOT_USERNAME + "?start=ref_" + str(uid)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📤 Share your link", switch_inline_query=link))
    bot.reply_to(message, "🎁 Invite friends, get bonus listings!\n\nFor every person who joins through your link, you both get +" + str(REFERRAL_BONUS) + " free listings.\n\nYour link:\n" + link, reply_markup=markup)

@bot.message_handler(commands=['history'])
def history_command(message):
    uid = message.from_user.id
    items = user_text_history.get(uid, [])
    if not items:
        bot.reply_to(message, "No saved listings yet. Create your first one!")
        return
    markup = InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(items):
        preview = item.replace("\n", " ")[:45]
        markup.add(InlineKeyboardButton(str(i + 1) + ") " + preview + "...", callback_data="hist_" + str(i)))
    bot.reply_to(message, "📜 Your recent listings — tap to load and continue editing:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("hist_"))
def history_callback(call):
    uid = call.from_user.id
    idx = int(call.data.replace("hist_", ""))
    items = user_text_history.get(uid, [])
    if idx >= len(items):
        bot.answer_callback_query(call.id, "Not found")
        return
    selected_text = items[idx]
    settings_ = get_settings(uid)
    user_history[uid] = [
        {"role": "system", "content": build_system_prompt(settings_)},
        {"role": "assistant", "content": selected_text}
    ]
    bot.answer_callback_query(call.id, "Loaded!")
    bot.send_message(call.message.chat.id, "✅ Listing loaded. You can now ask me to edit it:\n\n" + selected_text)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id != OWNER_ID:
        return
    active_subs = sum(1 for uid, exp in pro_users.items() if exp > datetime.now())
    bot.reply_to(message, "📊 Stats:\n\nTotal users: " + str(len(all_users)) + "\nActive subscriptions: " + str(active_subs) + "\nReferred: " + str(len(referred_by)))

@bot.message_handler(commands=['settings'])
def settings_command(message):
    uid = message.from_user.id
    s = get_settings(uid)
    bot.reply_to(message, SETTINGS_MAIN_TEXT, reply_markup=build_settings_main_markup())

@bot.message_handler(commands=['subscription'])
def subscription_command(message):
    bot.reply_to(message, get_sub_text(), reply_markup=build_sub_markup())

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, "Your Telegram ID: `" + str(message.from_user.id) + "`\n\nSend this to support if you paid via USDT.")

@bot.message_handler(commands=['activate'])
def activate(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 30
        expiry = datetime.now() + timedelta(days=days)
        pro_users[target_id] = expiry
        expiry_str = expiry.strftime("%m/%d/%Y")
        bot.reply_to(message, "Done. User " + str(target_id) + " active until " + expiry_str + ".")
        try:
            bot.send_message(target_id, "✅ Your EtsyScribe subscription is active until " + expiry_str + ". Happy selling! ✨")
        except Exception:
            pass
    except (IndexError, ValueError):
        bot.reply_to(message, "Use: /activate 123456789 30")

@bot.message_handler(commands=['deactivate'])
def deactivate(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        pro_users.pop(target_id, None)
        bot.reply_to(message, "Subscription for " + str(target_id) + " revoked.")
        try:
            bot.send_message(target_id, "Your EtsyScribe subscription was deactivated.")
        except Exception:
            pass
    except (IndexError, ValueError):
        bot.reply_to(message, "Use: /deactivate 123456789")

def send_out_of_requests(uid, chat_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💎 See subscription plans", callback_data="menu_subscription"),
        InlineKeyboardButton("🎁 Invite a friend for free listings", callback_data="menu_referral_hint")
    )
    bot.send_message(chat_id,
        "✨ You've used all 3 free listings!\n\n"
        "To keep writing listings without limits, choose a plan below.\n\n"
        "🗓 Monthly — 300 ⭐ (~$3.99)\n"
        "📅 6 Months — 1500 ⭐ (save 25%)\n"
        "🏆 Yearly — 2500 ⭐ (best value)\n\n"
        "Or invite a friend and get 2 more free listings for each referral.",
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "menu_referral_hint")
def referral_hint_callback(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    link = "https://t.me/" + BOT_USERNAME + "?start=ref_" + str(uid)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📤 Share your link", switch_inline_query=link))
    bot.send_message(call.message.chat.id, "Your referral link:\n" + link + "\n\nShare it and get +2 free listings for each person who joins!", reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id
    all_users.add(uid)
    if not is_unlimited(uid):
        left = get_free_left(uid)
        if left <= 0:
            send_out_of_requests(uid, message.chat.id)
            return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        b64_image = base64.b64encode(downloaded).decode('utf-8')
        caption = message.caption if message.caption else "Write a full Etsy listing for this item — title, description, and 13 tags."
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": "You are EtsyScribe, an expert Etsy listing writer. Look at the photo carefully. If the caption explicitly names the item, brand or material, trust that completely over your visual guess. Write a full Etsy listing: SEO title, emotional description, and 13 tags. Respond in English only."},
                {"role": "user", "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64_image}}
                ]}
            ],
            max_tokens=700
        )
        text = clean_text(response.choices[0].message.content)
        add_to_text_history(uid, text)
        if not is_unlimited(uid):
            user_free_left[uid] -= 1
            left = user_free_left[uid]
            footer = "\n\n─────────────────\n🎁 Free listings left: " + str(left) + " — /subscription for unlimited"
        else:
            footer = ""
        bot.reply_to(message, text + footer)
    except Exception:
        bot.reply_to(message, "Couldn't read the photo. Try again or describe the item in text.")

@bot.message_handler(func=lambda m: True)
def generate(message):
    uid = message.from_user.id
    all_users.add(uid)
    history = get_user_state(uid)
    settings_ = get_settings(uid)
    is_new_topic = len(history) == 0

    if not is_unlimited(uid) and is_new_topic:
        left = get_free_left(uid)
        if left <= 0:
            send_out_of_requests(uid, message.chat.id)
            return

    bot.send_chat_action(message.chat.id, 'typing')
    if is_new_topic:
        history.append({"role": "system", "content": build_system_prompt(settings_)})

    history.append({"role": "user", "content": message.text})
    trimmed = [history[0]] + history[-11:] if len(history) > 12 else history
    model_name = MODELS.get(settings_.get("model", "smart"), MODELS["smart"])

    try:
        response = client.chat.completions.create(model=model_name, messages=trimmed, max_tokens=800, temperature=0.8)
        text = clean_text(response.choices[0].message.content)
        history.append({"role": "assistant", "content": text})
        add_to_text_history(uid, text)

        if not is_unlimited(uid) and is_new_topic:
            user_free_left[uid] -= 1
            left = user_free_left[uid]
            footer = "\n\n─────────────────\n🎁 Free listings left: " + str(left) + " — /subscription for unlimited"
        else:
            footer = ""

        bot.reply_to(message, text + footer)
    except Exception:
        bot.reply_to(message, "Something went wrong, try again in a minute.")

print("EtsyScribe bot is running...")
bot.polling(none_stop=True)
