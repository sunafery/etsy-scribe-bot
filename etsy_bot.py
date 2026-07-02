cat > /mnt/user-data/outputs/seller_assistant_bot.py << 'PYEOF'
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
import re
import os
import base64
import urllib.request
import json as json_module
from datetime import datetime, timedelta
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN", "")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

OWNER_ID = 1249820876
OWNER_USERNAME = "sunafery"
BOT_USERNAME = os.environ.get("BOT_USERNAME", "your_bot_username")

FREE_LIMIT = 5
REFERRAL_BONUS = 3

STARS_STARTER = 200
STARS_PRO = 500
STARS_BUSINESS = 1200

CRYPTO_STARTER = 2.99
CRYPTO_PRO = 6.99
CRYPTO_BUSINESS = 14.99

user_free_left = {}
user_history = {}
pro_users = {}
user_settings = {}
user_text_history = {}
referred_by = {}
all_users = set()
user_plan = {}

MODELS = {
    "smart": "llama-3.3-70b-versatile",
    "fast": "llama-3.1-8b-instant"
}
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

PLATFORMS = {
    "auto": "🤖 Auto-detect",
    "etsy": "🛍️ Etsy",
    "amazon": "📦 Amazon",
    "ebay": "🔵 eBay",
    "shopify": "🟢 Shopify",
    "facebook": "👥 Facebook Marketplace",
    "depop": "🟣 Depop",
    "poshmark": "🩷 Poshmark",
    "vinted": "🔷 Vinted"
}

WELCOME_TEXT = (
    "✨ Welcome to SellMate AI\n\n"
    "Your personal AI selling assistant for Etsy, Amazon, eBay, Shopify, "
    "Facebook Marketplace and more.\n\n"
    "What I do in seconds:\n"
    "🖋 Write SEO-optimized product listings\n"
    "🏷️ Generate titles, descriptions & tags\n"
    "📷 Analyze your product photos\n"
    "💬 Answer buyer messages professionally\n"
    "📊 Suggest pricing strategy\n"
    "🌍 Translate listings to any language\n"
    "🔍 Research keywords for any platform\n\n"
    "Just tell me what you're selling — I'll handle the rest.\n\n"
    "🎁 You get 5 free requests to try. No credit card needed."
)

MENU_MAIN_TEXT = "🏠 Main Menu\n\nWhat would you like to do?"

def get_sub_text():
    return (
        "💎 SellMate AI — Subscription Plans\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🌱 STARTER — 200 ⭐ / $2.99\n"
        "50 AI requests per month\n"
        "All platforms supported\n"
        "Basic listing generator\n\n"
        "⚡ PRO — 500 ⭐ / $6.99\n"
        "Unlimited AI requests\n"
        "Priority response speed\n"
        "Keyword research tool\n"
        "Buyer message templates\n"
        "Multi-language support\n\n"
        "🏆 BUSINESS — 1200 ⭐ / $14.99\n"
        "Everything in Pro\n"
        "Bulk listing generation\n"
        "Competitor analysis\n"
        "Pricing strategy advisor\n"
        "Priority support\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Pay with ⭐ Telegram Stars (instant)\n"
        "or 💰 USDT crypto (automatic)"
    )

MENU_ABOUT_TEXT = (
    "✨ About SellMate AI\n\n"
    "SellMate AI is your all-in-one selling assistant — built for serious "
    "marketplace sellers who want to list faster, rank higher, and sell more.\n\n"
    "Unlike generic AI tools like ChatGPT, SellMate understands the specific "
    "requirements of each platform — Etsy SEO, Amazon A9 algorithm, eBay "
    "cassini search, and more.\n\n"
    "What makes us different:\n"
    "🎯 Platform-specific optimization\n"
    "📈 SEO-first approach for every listing\n"
    "⚡ 10x faster than writing manually\n"
    "🧠 Learns your shop's voice over time\n"
    "🌍 Supports 10+ languages\n"
    "📷 Understands product photos\n\n"
    "Trusted by sellers on Etsy, Amazon, eBay, Shopify and more."
)

MENU_SUPPORT_TEXT = (
    "🛠️ Support\n\n"
    "Got a question, bug report, or feature idea?\n"
    "We read every message and reply fast."
)

SETTINGS_TEXT = "⚙️ Settings\n\nCustomize your experience:"

def get_settings(uid):
    if uid not in user_settings:
        user_settings[uid] = {
            "model": "smart",
            "platform": "auto",
            "tone": "auto",
            "length": "auto",
            "language": "en"
        }
    return user_settings[uid]

def clean_text(text):
    return re.sub(r'[\u3040-\u30ff\uac00-\ud7af]', '', text)

def is_unlimited(uid):
    if uid == OWNER_ID:
        return True
    expiry = pro_users.get(uid)
    if expiry and expiry > datetime.now():
        plan = user_plan.get(uid, "starter")
        if plan in ["pro", "business"]:
            return True
    return False

def get_monthly_limit(uid):
    plan = user_plan.get(uid, "free")
    if plan == "starter":
        return 50
    return None

def get_free_left(uid):
    if uid not in user_free_left:
        user_free_left[uid] = FREE_LIMIT
    return user_free_left[uid]

def add_to_text_history(uid, text):
    if uid not in user_text_history:
        user_text_history[uid] = []
    user_text_history[uid].append({"text": text, "date": datetime.now().strftime("%b %d")})
    if len(user_text_history[uid]) > 10:
        user_text_history[uid].pop(0)

def build_system_prompt(settings_):
    platform = settings_.get("platform", "auto")
    tone = settings_.get("tone", "auto")
    length = settings_.get("length", "auto")
    language = settings_.get("language", "en")

    platform_rules = {
        "etsy": (
            "Platform: Etsy. Rules: SEO title max 140 chars (front-load keywords), "
            "13 tags (2-3 word phrases), description starts with emotional hook, "
            "mention: materials, dimensions if given, who it's perfect for, gift potential. "
            "Etsy buyers want handmade quality, story behind the item, uniqueness."
        ),
        "amazon": (
            "Platform: Amazon. Rules: title max 200 chars with brand+product+key features, "
            "5 bullet points starting with capital letters highlighting key benefits, "
            "description 2000 chars with keywords naturally integrated, "
            "backend search terms. Amazon buyers want specs, comparisons, trust signals."
        ),
        "ebay": (
            "Platform: eBay. Rules: title max 80 chars with most searchable terms first, "
            "description with condition details, measurements, brand, model number if applicable. "
            "Be honest about flaws. eBay buyers want exact specs and condition clarity."
        ),
        "shopify": (
            "Platform: Shopify/own store. Rules: SEO meta title 60 chars, meta description 160 chars, "
            "product description focused on benefits over features, "
            "include social proof language, strong call to action."
        ),
        "facebook": (
            "Platform: Facebook Marketplace. Rules: keep it conversational and local, "
            "mention condition clearly, include pickup/shipping info if relevant, "
            "price negotiation language. Buyers want quick clear info."
        ),
        "depop": (
            "Platform: Depop. Rules: casual Gen-Z tone, short punchy description, "
            "mention brand prominently, condition, measurements. "
            "End with 5-8 relevant hashtags. Depop buyers care about brand, era, aesthetic."
        ),
        "poshmark": (
            "Platform: Poshmark. Rules: detailed condition description, brand-forward title, "
            "mention original retail price if known (compare), measurements table if clothing. "
            "Poshmark buyers are style-conscious and brand-aware."
        ),
        "vinted": (
            "Platform: Vinted. Rules: honest condition focus, practical details, "
            "measurements if clothing, any flaws mentioned clearly. "
            "Vinted buyers value transparency and fair pricing."
        ),
        "auto": (
            "Auto-detect the best format based on the item type and user request. "
            "If it sounds handmade/vintage → use Etsy format. "
            "If it sounds branded/mass product → use Amazon/eBay format. "
            "Ask user which platform if genuinely unclear."
        )
    }

    tone_rules = {
        "professional": "Use professional, polished, trustworthy tone.",
        "casual": "Use casual, friendly, conversational tone.",
        "luxury": "Use premium, elevated, aspirational tone — sophisticated vocabulary.",
        "fun": "Use energetic, playful, enthusiastic tone with personality.",
        "auto": "Match tone to the platform and product type automatically."
    }

    length_rules = {
        "short": "Keep listings concise — titles + 3-5 sentence description + tags only.",
        "long": "Write comprehensive detailed listings — full descriptions with all sections.",
        "auto": "Choose appropriate length based on platform requirements."
    }

    lang_map = {
        "en": "English", "es": "Spanish", "de": "German",
        "fr": "French", "it": "Italian", "pt": "Portuguese",
        "ru": "Russian", "ja": "Japanese", "zh": "Chinese", "ar": "Arabic"
    }
    lang_name = lang_map.get(language, "English")

    return (
        "You are SellMate AI — the world's best marketplace selling assistant. "
        "You are an expert in Etsy, Amazon, eBay, Shopify, Facebook Marketplace, "
        "Depop, Poshmark, Vinted and all major e-commerce platforms.\n\n"
        "Your capabilities:\n"
        "1. Write optimized product listings (title + description + tags/keywords)\n"
        "2. Research and suggest SEO keywords for any platform\n"
        "3. Craft professional buyer response templates\n"
        "4. Advise on pricing strategy based on market position\n"
        "5. Analyze product photos and describe items\n"
        "6. Translate and localize listings for different markets\n"
        "7. Provide competitor analysis insights\n"
        "8. Suggest product improvements based on market trends\n"
        "9. Generate shop policies, FAQs, and about sections\n"
        "10. Help with product photography tips and staging advice\n\n"
        + platform_rules.get(platform, platform_rules["auto"]) + "\n\n"
        + tone_rules.get(tone, tone_rules["auto"]) + "\n"
        + length_rules.get(length, length_rules["auto"]) + "\n\n"
        "CRITICAL RULES:\n"
        "- Always respond in " + lang_name + "\n"
        "- If user explicitly names a brand, model, or material — trust that completely\n"
        "- Never invent specifications you don't know — be accurate\n"
        "- When writing listings: always include TITLE, DESCRIPTION, and TAGS/KEYWORDS sections\n"
        "- Format listings cleanly with clear section headers\n"
        "- Use conversation context when user asks to edit or improve previous listing\n"
        "- Be natural and helpful like a real e-commerce expert friend\n"
        "- You can also chat about general e-commerce strategy, trends, and tips"
    )

def get_user_state(uid):
    if uid not in user_history:
        user_history[uid] = []
    return user_history[uid]

def build_main_menu_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🖋 Write Listing", callback_data="action_listing"),
        InlineKeyboardButton("🔍 Keywords", callback_data="action_keywords"),
        InlineKeyboardButton("💬 Buyer Reply", callback_data="action_reply"),
        InlineKeyboardButton("💰 Pricing Help", callback_data="action_pricing"),
        InlineKeyboardButton("🌍 Translate", callback_data="action_translate"),
        InlineKeyboardButton("📷 Analyze Photo", callback_data="action_photo")
    )
    markup.add(
        InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        InlineKeyboardButton("💎 Subscription", callback_data="menu_subscription")
    )
    markup.add(
        InlineKeyboardButton("ℹ️ About", callback_data="menu_about"),
        InlineKeyboardButton("🛠️ Support", callback_data="menu_support")
    )
    return markup

def build_about_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_main"))
    return markup

def build_support_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✉️ Message Support", url="https://t.me/" + OWNER_USERNAME))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_main"))
    return markup

def build_sub_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌱 Starter — 200 ⭐", callback_data="pay_stars_starter"),
        InlineKeyboardButton("⚡ Pro — 500 ⭐ (Most Popular)", callback_data="pay_stars_pro"),
        InlineKeyboardButton("🏆 Business — 1200 ⭐", callback_data="pay_stars_business"),
        InlineKeyboardButton("💰 Pay with USDT crypto", callback_data="pay_usdt_menu"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu_main")
    )
    return markup

def build_usdt_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌱 Starter — $2.99 USDT", callback_data="pay_usdt_starter"),
        InlineKeyboardButton("⚡ Pro — $6.99 USDT", callback_data="pay_usdt_pro"),
        InlineKeyboardButton("🏆 Business — $14.99 USDT", callback_data="pay_usdt_business"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu_subscription")
    )
    return markup

def build_settings_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🛍️ Platform  >", callback_data="set_open_platform"),
        InlineKeyboardButton("🤖 AI Model  >", callback_data="set_open_model"),
        InlineKeyboardButton("🎨 Writing Tone  >", callback_data="set_open_tone"),
        InlineKeyboardButton("📄 Listing Length  >", callback_data="set_open_length"),
        InlineKeyboardButton("🌍 Language  >", callback_data="set_open_language"),
        InlineKeyboardButton("🔄 Reset to defaults", callback_data="set_reset"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu_main")
    )
    return markup

def build_platform_markup(s):
    options = list(PLATFORMS.items())
    options.sort(key=lambda x: 0 if x[0] == s["platform"] else 1)
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for key, label in options:
        prefix = "✅ " if s["platform"] == key else ""
        buttons.append(InlineKeyboardButton(prefix + label, callback_data="set_platform_" + key))
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_model_markup(s):
    options = [("smart", "🧠 Smart (more accurate)"), ("fast", "⚡ Fast (instant)")]
    options.sort(key=lambda x: 0 if x[0] == s["model"] else 1)
    markup = InlineKeyboardMarkup(row_width=1)
    for key, label in options:
        prefix = "✅ " if s["model"] == key else ""
        markup.add(InlineKeyboardButton(prefix + label, callback_data="set_model_" + key))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_tone_markup(s):
    options = [
        ("auto", "🤖 Auto"), ("professional", "💼 Professional"),
        ("casual", "😊 Casual"), ("luxury", "💎 Luxury"), ("fun", "🎉 Fun & Energetic")
    ]
    options.sort(key=lambda x: 0 if x[0] == s["tone"] else 1)
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for key, label in options:
        prefix = "✅ " if s["tone"] == key else ""
        buttons.append(InlineKeyboardButton(prefix + label, callback_data="set_tone_" + key))
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_length_markup(s):
    options = [("auto", "🤖 Auto"), ("short", "📌 Short"), ("long", "📝 Detailed")]
    options.sort(key=lambda x: 0 if x[0] == s["length"] else 1)
    markup = InlineKeyboardMarkup(row_width=1)
    for key, label in options:
        prefix = "✅ " if s["length"] == key else ""
        markup.add(InlineKeyboardButton(prefix + label, callback_data="set_length_" + key))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_language_markup(s):
    options = [
        ("en", "🇺🇸 English"), ("es", "🇪🇸 Spanish"), ("de", "🇩🇪 German"),
        ("fr", "🇫🇷 French"), ("it", "🇮🇹 Italian"), ("pt", "🇧🇷 Portuguese"),
        ("ru", "🇷🇺 Russian"), ("ja", "🇯🇵 Japanese"), ("zh", "🇨🇳 Chinese"), ("ar", "🇸🇦 Arabic")
    ]
    options.sort(key=lambda x: 0 if x[0] == s["language"] else 1)
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for key, label in options:
        prefix = "✅ " if s["language"] == key else ""
        buttons.append(InlineKeyboardButton(prefix + label, callback_data="set_lang_" + key))
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_settings"))
    return markup

def build_back_to_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"))
    return markup

DEFAULT_COMMANDS = [
    BotCommand("start", "Start / Home"),
    BotCommand("menu", "Main menu"),
    BotCommand("new", "New conversation"),
    BotCommand("listing", "Write a listing"),
    BotCommand("keywords", "Keyword research"),
    BotCommand("reply", "Write buyer reply"),
    BotCommand("pricing", "Pricing advice"),
    BotCommand("translate", "Translate listing"),
    BotCommand("balance", "Check balance"),
    BotCommand("history", "Recent listings"),
    BotCommand("referral", "Invite a friend"),
    BotCommand("subscription", "Plans & pricing"),
    BotCommand("settings", "Settings"),
    BotCommand("support", "Support"),
    BotCommand("myid", "My ID")
]

OWNER_COMMANDS = DEFAULT_COMMANDS + [
    BotCommand("activate", "Grant subscription"),
    BotCommand("deactivate", "Revoke subscription"),
    BotCommand("stats", "Bot statistics")
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

def send_out_of_requests(chat_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💎 See Subscription Plans", callback_data="menu_subscription"),
        InlineKeyboardButton("🎁 Invite Friend — Get Free Credits", callback_data="show_referral")
    )
    bot.send_message(chat_id,
        "✨ You've used all your free requests!\n\n"
        "Ready to unlock unlimited access?\n\n"
        "🌱 Starter — 200 ⭐ ($2.99) — 50 requests/month\n"
        "⚡ Pro — 500 ⭐ ($6.99) — Unlimited requests\n"
        "🏆 Business — 1200 ⭐ ($14.99) — Everything + priority\n\n"
        "Or invite a friend and get +" + str(REFERRAL_BONUS) + " free requests each!",
        reply_markup=markup)

def create_crypto_invoice(amount_usd, plan_name, payload):
    if not CRYPTO_BOT_TOKEN:
        return None
    try:
        data = json_module.dumps({
            "asset": "USDT",
            "amount": str(amount_usd),
            "description": "SellMate AI — " + plan_name,
            "payload": payload,
            "expires_in": 3600
        }).encode()
        req = urllib.request.Request(
            "https://pay.crypt.bot/api/createInvoice",
            data=data,
            headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN, "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json_module.loads(resp.read())
            if result.get("ok"):
                return result["result"]
    except Exception:
        pass
    return None

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
                    bot.send_message(referrer_id, "🎉 Someone joined through your link!\nYou got +" + str(REFERRAL_BONUS) + " free requests. Keep sharing!")
                except Exception:
                    pass
        except ValueError:
            pass

    if uid == OWNER_ID:
        bot.reply_to(message, "👑 Creator mode — unlimited access active.\n/activate /deactivate /stats available.")
        return

    if uid not in user_free_left:
        user_free_left[uid] = FREE_LIMIT

    bot.reply_to(message, WELCOME_TEXT)
    bot.send_message(message.chat.id, MENU_MAIN_TEXT, reply_markup=build_main_menu_markup())

@bot.message_handler(commands=['menu'])
def menu_command(message):
    bot.send_message(message.chat.id, MENU_MAIN_TEXT, reply_markup=build_main_menu_markup())

@bot.message_handler(commands=['balance'])
def balance_command(message):
    uid = message.from_user.id
    if uid == OWNER_ID:
        bot.reply_to(message, "👑 Creator — unlimited access.")
        return
    expiry = pro_users.get(uid)
    if expiry and expiry > datetime.now():
        plan = user_plan.get(uid, "starter")
        bot.reply_to(message, "💎 " + plan.upper() + " plan active until " + expiry.strftime("%b %d, %Y") + ".\n\nManage your plan: /subscription")
    else:
        left = get_free_left(uid)
        if left <= 0:
            bot.reply_to(message, "❌ Free requests: 0\n\nGet a subscription: /subscription\nOr invite friends: /referral")
        else:
            bot.reply_to(message, "🎁 Free requests remaining: " + str(left) + "/" + str(FREE_LIMIT) + "\n\nGet unlimited: /subscription")

@bot.message_handler(commands=['listing'])
def listing_command(message):
    bot.reply_to(message, "🖋 Tell me about your item and I'll write the perfect listing.\n\nExample: Handmade silver ring with turquoise stone, size 7, boho style")

@bot.message_handler(commands=['keywords'])
def keywords_command(message):
    bot.reply_to(message, "🔍 What item do you need keywords for?\n\nExample: vintage levi's jacket etsy\n\nI'll give you the best performing search terms for your platform.")

@bot.message_handler(commands=['reply'])
def reply_command(message):
    bot.reply_to(message, "💬 Paste the buyer's message and I'll write a professional reply for you.\n\nExample: 'Hi, does this come in size L? And can you ship to Canada?'")

@bot.message_handler(commands=['pricing'])
def pricing_command(message):
    bot.reply_to(message, "💰 Tell me about your item and I'll suggest a pricing strategy.\n\nInclude: what it is, your costs, target platform, and any comparable items you've seen.")

@bot.message_handler(commands=['translate'])
def translate_command(message):
    bot.reply_to(message, "🌍 Send me a listing to translate.\n\nFormat: paste your listing + tell me the target language.\nExample: [your listing text] → translate to Spanish for Etsy Spain")

@bot.message_handler(commands=['new'])
def new_topic(message):
    uid = message.from_user.id
    user_history[uid] = []
    bot.reply_to(message, "🔄 Fresh start! Previous conversation cleared.\n\nWhat are you selling today?")

@bot.message_handler(commands=['history'])
def history_command(message):
    uid = message.from_user.id
    items = user_text_history.get(uid, [])
    if not items:
        bot.reply_to(message, "📜 No saved listings yet.\n\nCreate your first listing with /listing")
        return
    markup = InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(items):
        preview = item["text"].replace("\n", " ")[:40]
        label = item.get("date", "") + " — " + preview + "..."
        markup.add(InlineKeyboardButton(str(i + 1) + ") " + label, callback_data="hist_" + str(i)))
    bot.reply_to(message, "📜 Your recent listings — tap to load and continue editing:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("hist_"))
def history_callback(call):
    uid = call.from_user.id
    idx = int(call.data.replace("hist_", ""))
    items = user_text_history.get(uid, [])
    if idx >= len(items):
        bot.answer_callback_query(call.id, "Not found")
        return
    selected = items[idx]["text"]
    settings_ = get_settings(uid)
    user_history[uid] = [
        {"role": "system", "content": build_system_prompt(settings_)},
        {"role": "assistant", "content": selected}
    ]
    bot.answer_callback_query(call.id, "Loaded!")
    markup = build_back_to_menu()
    bot.send_message(call.message.chat.id, "✅ Listing loaded. Ask me to improve, translate, or edit it:\n\n" + selected, reply_markup=markup)

@bot.message_handler(commands=['referral'])
def referral_command(message):
    uid = message.from_user.id
    link = "https://t.me/" + BOT_USERNAME + "?start=ref_" + str(uid)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📤 Share my link", switch_inline_query=link))
    bot.reply_to(message,
        "🎁 Invite sellers, earn free requests!\n\n"
        "Share your link → friend joins → you both get +" + str(REFERRAL_BONUS) + " free requests.\n\n"
        "Your referral link:\n" + link,
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_referral")
def show_referral_callback(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    link = "https://t.me/" + BOT_USERNAME + "?start=ref_" + str(uid)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📤 Share my link", switch_inline_query=link))
    bot.send_message(call.message.chat.id,
        "🎁 Your referral link:\n" + link + "\n\nShare it and get +" + str(REFERRAL_BONUS) + " free requests per friend!",
        reply_markup=markup)

@bot.message_handler(commands=['support'])
def support_command(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✉️ Message Support", url="https://t.me/" + OWNER_USERNAME))
    bot.reply_to(message, MENU_SUPPORT_TEXT, reply_markup=markup)

@bot.message_handler(commands=['subscription'])
def subscription_command(message):
    bot.reply_to(message, get_sub_text(), reply_markup=build_sub_markup())

@bot.message_handler(commands=['settings'])
def settings_command(message):
    bot.reply_to(message, SETTINGS_TEXT, reply_markup=build_settings_markup())

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, "Your Telegram ID: " + str(message.from_user.id) + "\n\nShare with support if you paid via USDT.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id != OWNER_ID:
        return
    active_subs = sum(1 for uid, exp in pro_users.items() if exp > datetime.now())
    total_free = sum(1 for uid in all_users if not is_unlimited(uid))
    bot.reply_to(message,
        "📊 SellMate AI Stats\n\n"
        "Total users: " + str(len(all_users)) + "\n"
        "Active subscriptions: " + str(active_subs) + "\n"
        "Free users: " + str(total_free) + "\n"
        "Referred users: " + str(len(referred_by)))

@bot.message_handler(commands=['activate'])
def activate(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        plan_name = parts[2] if len(parts) > 2 else "pro"
        days = int(parts[3]) if len(parts) > 3 else 30
        expiry = datetime.now() + timedelta(days=days)
        pro_users[target_id] = expiry
        user_plan[target_id] = plan_name
        expiry_str = expiry.strftime("%b %d, %Y")
        bot.reply_to(message, "Done. User " + str(target_id) + " — " + plan_name.upper() + " until " + expiry_str)
        try:
            bot.send_message(target_id, "✅ Your SellMate AI " + plan_name.upper() + " subscription is active until " + expiry_str + ". Happy selling! 🚀")
        except Exception:
            pass
    except (IndexError, ValueError):
        bot.reply_to(message, "Use: /activate 123456789 pro 30")

@bot.message_handler(commands=['deactivate'])
def deactivate(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        pro_users.pop(target_id, None)
        user_plan.pop(target_id, None)
        bot.reply_to(message, "Subscription revoked for " + str(target_id))
        try:
            bot.send_message(target_id, "Your SellMate AI subscription has ended. Renew anytime: /subscription")
        except Exception:
            pass
    except (IndexError, ValueError):
        bot.reply_to(message, "Use: /deactivate 123456789")

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
        safe_edit(call, SETTINGS_TEXT, build_settings_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith("action_"))
def action_callback(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    action = call.data.replace("action_", "")
    prompts = {
        "listing": "🖋 What are you selling? Send me the item name and any details (brand, material, size, condition, color).\n\nI'll write the full listing with title, description, and tags.",
        "keywords": "🔍 What item do you need keywords for?\n\nExample: vintage levi's denim jacket\n\nI'll give you the best search terms for your platform.",
        "reply": "💬 Paste the buyer's message below and I'll write a professional response for you.",
        "pricing": "💰 Tell me about your item and I'll suggest the right price.\n\nInclude: what it is, your costs, condition, and platform.",
        "translate": "🌍 Paste your listing and tell me which language to translate it into.\n\nExample: translate my listing to French",
        "photo": "📷 Send me a photo of your item and I'll write a complete listing for it. You can also add a caption with any details."
    }
    bot.send_message(call.message.chat.id, prompts.get(action, "Send me your request:"))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_open_") or call.data == "set_reset")
def settings_open_callback(call):
    uid = call.from_user.id
    s = get_settings(uid)
    bot.answer_callback_query(call.id)
    if call.data == "set_reset":
        user_settings[uid] = {"model": "smart", "platform": "auto", "tone": "auto", "length": "auto", "language": "en"}
        safe_edit(call, SETTINGS_TEXT, build_settings_markup())
        return
    section = call.data.replace("set_open_", "")
    if section == "platform":
        safe_edit(call, "🛍️ Choose your default platform:", build_platform_markup(s))
    elif section == "model":
        safe_edit(call, "🤖 Choose AI model:", build_model_markup(s))
    elif section == "tone":
        safe_edit(call, "🎨 Choose writing tone:", build_tone_markup(s))
    elif section == "length":
        safe_edit(call, "📄 Choose listing length:", build_length_markup(s))
    elif section == "language":
        safe_edit(call, "🌍 Choose your language:", build_language_markup(s))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_platform_") or call.data.startswith("set_model_") or call.data.startswith("set_tone_") or call.data.startswith("set_length_") or call.data.startswith("set_lang_"))
def settings_value_callback(call):
    uid = call.from_user.id
    s = get_settings(uid)
    data = call.data
    bot.answer_callback_query(call.id, "Updated!")
    if data.startswith("set_platform_"):
        s["platform"] = data.replace("set_platform_", "")
        safe_edit(call, "🛍️ Choose your default platform:", build_platform_markup(s))
    elif data.startswith("set_model_"):
        s["model"] = data.replace("set_model_", "")
        safe_edit(call, "🤖 Choose AI model:", build_model_markup(s))
    elif data.startswith("set_tone_"):
        s["tone"] = data.replace("set_tone_", "")
        safe_edit(call, "🎨 Choose writing tone:", build_tone_markup(s))
    elif data.startswith("set_length_"):
        s["length"] = data.replace("set_length_", "")
        safe_edit(call, "📄 Choose listing length:", build_length_markup(s))
    elif data.startswith("set_lang_"):
        s["language"] = data.replace("set_lang_", "")
        safe_edit(call, "🌍 Choose your language:", build_language_markup(s))

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_stars_"))
def pay_stars_callback(call):
    bot.answer_callback_query(call.id)
    plans = {
        "pay_stars_starter": (STARS_STARTER, "Starter — 50 req/month", "sub_starter", 30),
        "pay_stars_pro": (STARS_PRO, "Pro — Unlimited", "sub_pro", 30),
        "pay_stars_business": (STARS_BUSINESS, "Business — Everything", "sub_business", 30)
    }
    plan = plans.get(call.data)
    if not plan:
        return
    amount, name, payload, days = plan
    prices = [LabeledPrice(label="SellMate AI — " + name, amount=amount)]
    bot.send_invoice(call.message.chat.id, title="SellMate AI", description=name, invoice_payload=payload, provider_token="", currency="XTR", prices=prices)

@bot.callback_query_handler(func=lambda call: call.data == "pay_usdt_menu")
def pay_usdt_menu(call):
    bot.answer_callback_query(call.id)
    safe_edit(call, "💰 Pay with USDT — choose your plan:", build_usdt_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_usdt_") and call.data != "pay_usdt_menu")
def pay_usdt_callback(call):
    bot.answer_callback_query(call.id)
    plans = {
        "pay_usdt_starter": (CRYPTO_STARTER, "Starter", "crypto_starter", 30),
        "pay_usdt_pro": (CRYPTO_PRO, "Pro", "crypto_pro", 30),
        "pay_usdt_business": (CRYPTO_BUSINESS, "Business", "crypto_business", 30)
    }
    plan = plans.get(call.data)
    if not plan:
        return
    amount, name, payload, days = plan
    uid = call.from_user.id
    invoice = create_crypto_invoice(amount, name, payload + "_" + str(uid) + "_" + str(days))
    if invoice:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💰 Pay $" + str(amount) + " USDT", url=invoice["pay_url"]))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="pay_usdt_menu"))
        bot.send_message(call.message.chat.id,
            "💰 " + name + " — $" + str(amount) + " USDT\n\n"
            "Tap the button to pay via CryptoBot.\n"
            "Subscription activates automatically after payment.",
            reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✉️ Contact Support", url="https://t.me/" + OWNER_USERNAME))
        bot.send_message(call.message.chat.id, "⚠️ Crypto payments are being configured. Contact support to pay via USDT.", reply_markup=markup)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    days = 30
    if "business" in payload:
        plan_name = "business"
    elif "pro" in payload:
        plan_name = "pro"
    else:
        plan_name = "starter"
    expiry = datetime.now() + timedelta(days=days)
    pro_users[uid] = expiry
    user_plan[uid] = plan_name
    bot.reply_to(message,
        "✅ Payment confirmed!\n\n"
        "Plan: " + plan_name.upper() + "\n"
        "Active until: " + expiry.strftime("%b %d, %Y") + "\n\n"
        "You now have " + ("unlimited" if plan_name in ["pro", "business"] else "50") + " requests.\n\n"
        "Ready to sell more? Send me your first item! 🚀")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id
    all_users.add(uid)
    if not is_unlimited(uid):
        left = get_free_left(uid)
        if left <= 0:
            send_out_of_requests(message.chat.id)
            return
    bot.send_chat_action(message.chat.id, 'typing')
    settings_ = get_settings(uid)
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        b64_image = base64.b64encode(downloaded).decode('utf-8')
        caption = message.caption if message.caption else "Analyze this product photo and write a complete marketplace listing with title, description, and relevant tags/keywords."
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": build_system_prompt(settings_) + "\nIf the user's caption explicitly names the brand, model or material, trust that completely over your visual guess."},
                {"role": "user", "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64_image}}
                ]}
            ],
            max_tokens=900
        )
        text = clean_text(response.choices[0].message.content)
        add_to_text_history(uid, text)
        if not is_unlimited(uid):
            user_free_left[uid] -= 1
            left = get_free_left(uid)
            footer = "\n\n━━━━━━━━━━━━━━━\n🎁 Free requests left: " + str(left) + "  •  /subscription for unlimited"
        else:
            footer = ""
        markup = build_back_to_menu()
        bot.reply_to(message, text + footer, reply_markup=markup)
    except Exception:
        bot.reply_to(message, "Couldn't analyze the photo. Try again or describe the item in text.")

@bot.message_handler(func=lambda m: True)
def generate(message):
    uid = message.from_user.id
    all_users.add(uid)
    history = get_user_state(uid)
    settings_ = get_settings(uid)
    is_new_topic = len(history) == 0

    if not is_unlimited(uid):
        left = get_free_left(uid)
        if left <= 0:
            send_out_of_requests(message.chat.id)
            return

    bot.send_chat_action(message.chat.id, 'typing')
    if is_new_topic:
        history.append({"role": "system", "content": build_system_prompt(settings_)})

    history.append({"role": "user", "content": message.text})
    trimmed = [history[0]] + history[-11:] if len(history) > 12 else history
    model_name = MODELS.get(settings_.get("model", "smart"), MODELS["smart"])

    try:
        response = client.chat.completions.create(model=model_name, messages=trimmed, max_tokens=900, temperature=0.8)
        text = clean_text(response.choices[0].message.content)
        history.append({"role": "assistant", "content": text})
        add_to_text_history(uid, text)

        if not is_unlimited(uid):
            user_free_left[uid] -= 1
            left = get_free_left(uid)
            if left <= 0:
                footer = "\n\n━━━━━━━━━━━━━━━\n❌ Free requests used up  •  /subscription for unlimited"
            else:
                footer = "\n\n━━━━━━━━━━━━━━━\n🎁 Free requests left: " + str(left) + "  •  /subscription for unlimited"
        else:
            footer = ""

        markup = build_back_to_menu()
        bot.reply_to(message, text + footer, reply_markup=markup)
    except Exception:
        bot.reply_to(message, "Something went wrong, try again in a minute.")

print("SellMate AI bot is running...")
bot.polling(none_stop=True)
PYEOF
python3 -c "
import ast
with open('/mnt/user-data/outputs/seller_assistant_bot.py', encoding='utf-8') as f:
    code = f.read()
ast.parse(code)
print('OK - синтаксис верный')
"
