import os
import re
import requests
import telebot
from threading import Thread
from flask import Flask

# Flask Web Server (Render Free tier kosam)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Telegram Bot Logic
BOT_TOKEN =9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_msg(message):
    bot.reply_to(message, "హలో! Pocket FM ఎపిసోడ్ లింక్ పంపండి, ఆడియో తీసి ఇస్తాను.")

@bot.message_handler(func=lambda msg: True)
def download_audio(message):
    url = message.text.strip()
    chat_id = message.chat.id

    if "pocketfm" not in url:
        bot.reply_to(message, "దయచేసి సరైన Pocket FM లింక్ మాత్రమే పంపండి.")
        return

    wait_msg = bot.reply_to(message, "ఆడియో వెతుకుతున్నాను... ఆగండి.")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=20)
        audio_urls = re.findall(r'https?://[^\s",\']+\.mp3[^\s",\']*', res.text)

        if not audio_urls:
            bot.edit_message_text("ఆడియో దొరకలేదు లేదా ఇది లాక్ చేయబడిన ఎపిసోడ్.", chat_id=chat_id, message_id=wait_msg.message_id)
            return

        file_path = f"audio_{chat_id}_{message.message_id}.mp3"
        bot.edit_message_text("డౌన్‌లోడ్ అవుతోంది...", chat_id=chat_id, message_id=wait_msg.message_id)

        audio_res = requests.get(audio_urls[0], stream=True, timeout=60)
        with open(file_path, "wb") as f:
            for chunk in audio_res.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        with open(file_path, "rb") as audio:
            bot.send_audio(chat_id, audio, caption="మీ ఆడియో సిద్ధమైంది!")

        if os.path.exists(file_path):
            os.remove(file_path)

        bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"సమస్య వచ్చింది: {str(e)}", chat_id=chat_id, message_id=wait_msg.message_id)

if __name__ == "__main__":
    # Web server ni background lo start chestunnam
    Thread(target=run_web).start()
    # Bot polling
    bot.infinity_polling()
