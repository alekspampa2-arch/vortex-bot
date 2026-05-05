# -*- coding: utf-8 -*-
"""
VORTEX AFFILIATES — Telegram Bot
Запуск: pip install pyTelegramBotAPI requests && python3 vortex_bot.py

Что делает бот:
- Партнёр пишет /start → бот генерирует 6-значный код
- Код сохраняется в Supabase (таблица tg_connect_codes)
- Партнёр вводит код in the dashboard → его chat_id привязывается к аккаунту
- После привязки бот отправляет уведомления автоматически через Edge Function
"""

import telebot
import requests
import random
import string
from datetime import datetime

# ── CONFIG ─────────────────────────────────────────────────────────────────
BOT_TOKEN     = "8652899701:AAFaIhpXkkmulmdJjvGxS2CYQ3ANA8T5bKI"
ADMIN_CHAT_ID = 6858727663  # Aleksey          # Токен от @BotFather
SB_URL     = "https://nkhcvlggwektgzzkvunq.supabase.co"
SB_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5raGN2bGdnd2VrdGd6emt2dW5xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2NjAyMjcsImV4cCI6MjA5MzIzNjIyN30.uJQpNHJ6pXyZs0YZ2K5ppzpo8eVe06uWnE-z1u9iweI"
DASHBOARD  = "https://flourishing-travesseiro-b6bbb7.netlify.app"

bot = telebot.TeleBot(BOT_TOKEN)

def sb_req(path, method="GET", data=None):
    """Make request to Supabase REST API"""
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = SB_URL + path
    if method == "GET":
        r = requests.get(url, headers=headers)
    elif method == "POST":
        r = requests.post(url, headers=headers, json=data)
    elif method == "PATCH":
        r = requests.patch(url, headers=headers, json=data)
    elif method == "DELETE":
        r = requests.delete(url, headers=headers)
    return r

def generate_code():
    """Generate 6-digit numeric code"""
    return ''.join(random.choices(string.digits, k=6))

def save_code(chat_id, code):
    """Save connect code to Supabase"""
    # Delete old codes for this chat_id
    sb_req(f"/rest/v1/tg_connect_codes?chat_id=eq.{chat_id}&used=eq.false", method="DELETE")
    # Insert new code
    sb_req("/rest/v1/tg_connect_codes", method="POST", data={
        "code": code,
        "chat_id": chat_id,
        "used": False
    })

def check_connected(chat_id):
    """Check if this chat_id is already connected to an account"""
    r = sb_req(f"/rest/v1/profiles?tg_chat_id=eq.{chat_id}&select=full_name,email&limit=1")
    if r.ok:
        data = r.json()
        if data:
            return data[0]
    return None

# ── HANDLERS ───────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    
    # Check if already connected
    profile = check_connected(chat_id)
    if profile:
        name = profile.get('full_name') or profile.get('email', 'Partner')
        bot.reply_to(message, 
            f"✅ *Already connected!*\n\n"
            f"Account: *{name}*\n\n"
            f"You will receive notifications about conversions and payouts.\n\n"
            f"[Open dashboard]({DASHBOARD})",
            parse_mode="Markdown"
        )
        return
    
    # Generate new code
    code = generate_code()
    save_code(chat_id, code)
    
    bot.reply_to(message,
        f"⬡ *Vortex Affiliates*\n\n"
        f"Hello! Я бот для уведомлений партнёрской программы.\n\n"
        f"Your connection code:\n\n"
        f"```\n{code}\n```\n\n"
        f"Enter this code in the *Profile* → *Telegram Notifications* in the dashboard.\n\n"
        f"⏰ Code is valid for *10 minutes*.\n\n"
        f"[Open dashboard]({DASHBOARD})",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['status'])
def handle_status(message):
    chat_id = message.chat.id
    profile = check_connected(chat_id)
    
    if profile:
        name = profile.get('full_name') or profile.get('email', 'Partner')
        bot.reply_to(message,
            f"✅ *Connected*\n\nAccount: *{name}*\n\n[Dashboard]({DASHBOARD})",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message,
            f"❌ *Not connected*\n\nSend /start чтобы get connection code.",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['disconnect'])
def handle_disconnect(message):
    chat_id = message.chat.id
    profile = check_connected(chat_id)
    
    if not profile:
        bot.reply_to(message, "Account was not connected.")
        return
    
    # Find and disconnect
    r = sb_req(f"/rest/v1/profiles?tg_chat_id=eq.{chat_id}&select=id&limit=1")
    if r.ok and r.json():
        aff_id = r.json()[0]['id']
        sb_req(f"/rest/v1/profiles?id=eq.{aff_id}", method="PATCH", data={"tg_chat_id": None})
        bot.reply_to(message, "✅ Telegram disconnected from account. Notifications disabled.")
    else:
        bot.reply_to(message, "Error. Please try again.")

@bot.message_handler(commands=['newcode'])
def handle_newcode(message):
    """Generate a new connect code"""
    handle_start(message)

@bot.message_handler(func=lambda m: True)
def handle_any(message):
    bot.reply_to(message,
        f"⬡ *Vortex Affiliates Bot*\n\n"
        f"Commands:\n"
        f"/start — get connection code\n"
        f"/status — connection status\n"
        f"/newcode — new code\n"
        f"/disconnect — disable notifications",
        parse_mode="Markdown"
    )

# ── RUN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    print("=" * 50)
    print("  Vortex Affiliates Bot")
    print("=" * 50)
    
    # Test bot connection
    try:
        me = bot.get_me()
        print(f"Bot: @{me.username} (ID: {me.id})")
        print(f"Status: ONLINE")
        print(f"Dashboard: {DASHBOARD}")
        print("=" * 50)
        print("Bot is running... Press Ctrl+C to stop")
        print()
        try:
            bot.send_message(ADMIN_CHAT_ID,
                "⛡ Vortex Bot started!\n\n✅ Bot is online",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"ERROR: {e}")
        print()
        print("Possible causes:")
        print("  1. No internet connection")
        print("  2. Wrong bot token")
        print("  3. Bot token was revoked")
        print()
        print("Get new token from @BotFather")
        input("Press Enter to exit...")
        sys.exit(1)
