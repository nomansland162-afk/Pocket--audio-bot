import os
import re
import requests
import telebot
from threading import Thread
from flask import Flask

# Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# మీ BotFather టోకెన్
BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGiZH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_msg(message):
    bot.reply_to(message, "బాట్ ఆన్‌లైన్‌లో ఉంది! మీరు ఏదైనా సందేశం పంపవచ్చు.")

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    text = message.text.strip()
    
    # మెసేజ్ నుండి కేవలం URL ను మాత్రమే వేరు చేయడం (Extract clean URL)
    url_match = re.search(r'(https?://[^\s]+)', text)
    
    if not url_match:
        bot.reply_to(message, "దయచేసి సరైన వెబ్‌సైట్ లింక్ మాత్రమే పంపండి.")
        return
        
    clean_url = url_match.group(1)
    bot.reply_to(message, f"మీరు పంపిన లింక్ అందింది: {clean_url}")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
