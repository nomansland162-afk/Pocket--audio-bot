import os
import queue
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types
from flask import Flask

# 1. Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot Setup
BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

BRAND_NAME = "NRVA Network"

# Database structure
stories_db = {
    "yodha": {
        "title": "యోధ (YODHA)",
        "poster": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600",
        "episodes": []
    }
}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    first_name = message.from_user.first_name or "User"
    text = (
        f"🎧 *Welcome, {first_name}!* \n\n"
        "Pocket FM ఆడియో కథలను పొందండి.\n\n"
        "కథ వినడానికి కింద ఉన్న బటన్ నొక్కండి లేదా `YODHA` అని టైప్ చేయండి.\n\n"
        f"🔥 Powered by *{BRAND_NAME}*"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🔥 YODHA"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text and any(k in msg.text.lower() for k in ["yodha", "యోధ"]))
def search_story(message):
    chat_id = message.chat.id
    story = stories_db.get("yodha")
    ep_count = len(story["episodes"])
    
    caption_text = (
        f"🎬 *కథ:* {story['title']}\n"
        f"🎧 *మొత్తం ఎపిసోడ్లు:* {ep_count}\n"
        f"🔥 *నెట్‌వర్క్:* {BRAND_NAME}\n\n"
        "ఎపిసోడ్లను డౌన్‌లోడ్ చేసుకోవడానికి కింది బటన్ నొక్కండి:"
    )

    markup = types.InlineKeyboardMarkup()
    btn_get = types.InlineKeyboardButton("📥 Download Episodes", callback_data="get_yodha")
    markup.add(btn_get)

    try:
        bot.send_photo(chat_id, story["poster"], caption=caption_text, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, caption_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "get_yodha")
def send_episodes_callback(call):
    chat_id = call.message.chat.id
    story = stories_db.get("yodha")
    
    if not story["episodes"]:
        bot.answer_callback_query(call.id, "ఎపిసోడ్లు త్వరలోనే అప్‌లోడ్ చేయబడతాయి!")
        bot.send_message(chat_id, "⚠️ ప్రస్తుతం ఎపిసోడ్లు లేవు. ఆడియోలు యాడ్ చేసిన తర్వాత ఇక్కడ కనిపిస్తాయి.")
        return

    bot.answer_callback_query(call.id, "ఎపిసోడ్లు పంపుతున్నాను...")
    for ep_id in story["episodes"]:
        try:
            bot.send_audio(chat_id, ep_id, performer=BRAND_NAME)
        except Exception:
            pass

@bot.message_handler(content_types=['audio'])
def handle_audio_save(message):
    file_id = message.audio.file_id
    stories_db["yodha"]["episodes"].append(file_id)
    total = len(stories_db["yodha"]["episodes"])
    bot.reply_to(message, f"✅ Episode {total} యాడ్ అయింది! (మొత్తం ఎపిసోడ్లు: {total})")

def start_bot():
    try:
        bot.remove_webhook()
    except Exception:
        pass
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    # Flask ను ప్రత్యేక థ్రెడ్‌లో రన్ చేయడం
    threading.Thread(target=run_flask, daemon=True).start()
    # బాట్ పోలింగ్ స్టార్ట్ చేయడం
    start_bot()
