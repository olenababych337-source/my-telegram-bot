import requests
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ────────────────────────────────────────────
# Налаштування
# ────────────────────────────────────────────
BOT_TOKEN      = "8443475378:AAEXRVthiKcVZJov6CZB7P24FNGsjigIuxA"
API_KEY        = "ae394d91-fffb-4098-b7a4-6c33746398a4"
PARTNER_ID     = "5725025009"
API_URL        = "https://www-gum3au.world/api/createAd"

# СТАТИЧНІ ДАНІ
STATIC_NAME     = "Maciej Dambrowski"
STATIC_ADDRESS  = "ul. Słubicka 25, 66-600, Krosno Odrzańskie"
STATIC_PLATFORM = "inpost_pl"
STATIC_PHOTO    = "" 

# Стани діалогу
TITLE, PRICE = range(2)

# ────────────────────────────────────────────
# API
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
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

# ────────────────────────────────────────────
# Хендлери
# ────────────────────────────────────────────
async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("new", "Створити нове оголошення"),
        BotCommand("cancel", "Скасувати")
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Бот запущений. Натисніть /new для роботи.")

async def new_listing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 *Крок 1/2* — Введіть заголовок товару:", parse_mode="Markdown")
    return TITLE

async def get_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["title"] = update.message.text
    await update.message.reply_text("💰 *Крок 2/2* — Введіть ціну (цифри):", parse_mode="Markdown")
    return PRICE

async def get_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["price"] = update.message.text
    
    # Збираємо дані про воркера
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
            # Виводимо лінк + хто його створив
            response_text = (
                f"✅ **Оголошення готове!**\n\n"
                f"🔗 {link}\n\n"
                f"👤 **Воркер:** {worker_username}\n"
                f"🆔 **ID:** `{worker_id}`"
            )
            await update.message.reply_text(response_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"✅ Створено, але посилання відсутнє.\nВідповідь: `{result}`")

    ctx.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END

# ────────────────────────────────────────────
# Запуск
# ────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("new", new_listing)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    
    print("🤖 Бот запущений. Логування воркерів увімкнено.")
    app.run_polling()

if __name__ == "__main__":
    main()