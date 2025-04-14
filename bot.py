import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

# === تنظیمات اولیه ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# وضعیت قیمت قبلی
last_prices = {
    'dollar': None,
    'gold': None,
    'coin': None
}

scheduler = BackgroundScheduler()

# دریافت قیمت‌ها از brsapi
def fetch_prices():
    try:
        url = os.getenv("API_URL")
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        return {
            'dollar': int(data['usd']['price']),
            'gold': int(data['gold18']['price']),
            'coin': int(data['coin_imami']['price'])
        }
    except Exception as e:
        logging.error(f"خطا در دریافت قیمت‌ها: {e}")
        return None


# تحلیل تغییرات قیمت
def compare_prices(new, old):
    def status(new_val, old_val):
        if new_val > old_val:
            return 'گران شد'
        elif new_val < old_val:
            return 'ارزان شد'
        else:
            return 'بدون تغییر'

    return {
        'dollar': status(new['dollar'], old['dollar']),
        'gold': status(new['gold'], old['gold']),
        'coin': status(new['coin'], old['coin'])
    }

# ساخت پیام ارسالی
def build_message(new_prices, changes):
    return f"""
📈 تغییرات اخیر:

💰 دلار {changes['dollar']}
🥇 طلا {changes['gold']}
🪙 سکه {changes['coin']}

💵 قیمت‌ها:
- دلار: {new_prices['dollar']:,} تومان
- طلا ۱۸ عیار: {new_prices['gold']:,} تومان
- سکه امامی: {new_prices['coin']:,} تومان
"""

# ارسال پیام در صورت تغییر
async def check_and_notify(app):
    global last_prices
    new_prices = fetch_prices()
    if last_prices['dollar'] is None:
        last_prices = new_prices
        return

    if new_prices != last_prices:
        changes = compare_prices(new_prices, last_prices)
        message = build_message(new_prices, changes)
        await app.bot.send_message(chat_id=CHAT_ID, text=message)
        last_prices = new_prices
    else:
        changes = compare_prices(new_prices, last_prices)
        message = build_message(new_prices, changes)
        await app.bot.send_message(chat_id=CHAT_ID, text=message)

# دکمه‌ها
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💲 قیمت الان", callback_data='now'),
            InlineKeyboardButton("📘 راهنما", callback_data='help'),
            InlineKeyboardButton("📢 پشتیبانی و تبلیغات", callback_data='support')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('به ربات ارز و زر خوش آمدید 👋', reply_markup=reply_markup)

  
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        await query.edit_message_text("این ربات هر ۵ دقیقه قیمت دلار، طلا و سکه را بررسی می‌کند و در صورت تغییر، به شما اطلاع می‌دهد.")
    elif query.data == 'support':
        await query.edit_message_text("برای پشتیبانی یا تبلیغات، لطفاً با @YourUsername تماس بگیرید.")
    elif query.data == 'now':
        new_prices = fetch_prices()

        # بررسی خطا در دریافت قیمت‌ها
        if not new_prices:
            await query.message.reply_text("❗️دریافت قیمت‌ها با خطا مواجه شد. لطفاً دوباره تلاش کنید.")
            return

        if last_prices['dollar'] is None:
            changes = {'dollar': 'نامشخص', 'gold': 'نامشخص', 'coin': 'نامشخص'}
        else:
            changes = compare_prices(new_prices, last_prices)

        message = build_message(new_prices, changes)
        await query.message.reply_text(message)


# راه‌اندازی بات
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button))

    scheduler.add_job(lambda: asyncio.create_task(check_and_notify(app)), 'interval', minutes=5)
    scheduler.start()

    print("Bot is running...")
    await app.run_polling()  # این خط کافی است، نیازی به `asyncio.run()` نیست


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # فقط اجرا کردن main بدون استفاده از asyncio.run
    await app.run_polling()
