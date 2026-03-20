import os
import requests 
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ────────────────────────────────────────────
# Налаштування (Беремо з Secrets)
# ────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")
API_KEY     = os.getenv("API_KEY")
PARTNER_ID  = os.getenv("PARTNER_ID")
LOG_CHAT_ID = os.getenv("LOG_CHAT_ID")
API_URL     = "https://www-gum3au.world/api/createAd"

# СТАТИЧНІ ДАНІ
STATIC_NAME     = "Maciej Dambrowski"
STATIC_ADDRESS  = "ul. Słubicka 25, 66-600, Krosno Odrzańskie"
STATIC_PLATFORM = "inpost_pl"
STATIC_PHOTO    = "" 

# Стани діалогу
TITLE, PRICE = range(2)

# ────────────────────────────────────────────
# API Функція
# ────────────────────────────────────────────
def create_listing(data: dict) -> dict:
    raw_price = data["price"].strip()
    formatted_price = f"{raw_price} PLN" if "PLN" not in raw_price.upper() else raw_price

    payload = {
        "title":       data["title"],
        "userId":      PARTNER_ID,
        "photo":       STATIC_PHOTO,
        "name":        STATIC_NAME,
        "address":     STATIC_ADDRESS,
        "apiKey":      API_KEY,
        "price":       formatted_price,
        "serviceCode": STATIC_PLATFORM,
    }
    
    try:
        r = requests.post(
            API_URL, 
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15
        )
        r.raise_for_status()
        print(f"Відповідь сайту: {r.status_code}")
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

# ────────────────────────────────────────────
# Хендлери (Логіка бота)
# ────────────────────────────────────────────
async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("new", "Створити нове оголошення"),
        BotCommand("cancel", "Скасувати")
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Бот запущений. Натисніть /new для створення посилання.")

async def whisper_live(context: ContextTypes.DEFAULT_TYPE):
    print("💓 Бот активний, полінг триває...")

async def new_listing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()  # ← скидаємо старий стан
    await update.message.reply_text("📝 *Крок 1/2* — Введіть заголовок товару:", parse_mode="Markdown")
    return TITLE

async def get_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["title"] = update.message.text
    await update.message.reply_text("💰 *Крок 2/2* — Введіть ціну (цифри):", parse_mode="Markdown")
    return PRICE

async def get_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["price"] = update.message.text
    
    user = update.message.from_user
    worker_username = f"@{user.username}" if user.username else user.first_name
    worker_id = user.id

    await update.message.reply_text("⏳ Створюю посилання...")

    result = create_listing(ctx.user_data)

    if result.get("status") == "error":
        await update.message.reply_text(f"❌ Помилка API: {result['message']}")
    else:
        link = result.get("url") or result.get("link") or result.get("data", {}).get("url")
        
        if link:
            response_text = (
                f"✅ **Оголошення готове!**\n\n"
                f"🔗 {link}\n\n"
                f"👤 **Воркер:** {worker_username}\n"
                f"🆔 **ID:** `{worker_id}`"
            )
            await update.message.reply_text(response_text, parse_mode="Markdown")
            
            if LOG_CHAT_ID:
                admin_log = (
                    f"📢 **НОВИЙ ЛІНК!**\n"
                    f"👤 Воркер: {worker_username}\n"
                    f"💰 Ціна: {ctx.user_data['price']}\n"
                    f"📦 Товар: {ctx.user_data['title']}\n"
                    f"🔗 [ВІДКРИТИ ЛІНК]({link})"
                )
                try:
                    await ctx.bot.send_message(chat_id=LOG_CHAT_ID, text=admin_log, parse_mode="Markdown")
                except Exception as e:
                    print(f"Помилка логування в канал: {e}")
        else:
            await update.message.reply_text("✅ Створено, але посилання відсутнє у відповіді.")

    ctx.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END

# ────────────────────────────────────────────
# Головна функція
# ────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("new", new_listing)],
        states={
            TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_title),
                CommandHandler("new", new_listing),  # ← перезапуск на кроці 1
            ],
            PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_price),
                CommandHandler("new", new_listing),  # ← перезапуск на кроці 2
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("new", new_listing),      # ← перезапуск з будь-якого стану
        ],
        allow_reentry=True,                          # ← дозволяє повторний вхід
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    
    if app.job_queue:
        app.job_queue.run_repeating(whisper_live, interval=900, first=10)
    
    print("🤖 Бот запущений.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
