import os
import re
import requests
import telebot
from threading import Thread
from flask import Flask

# Flask సర్వర్ (24/7 లైవ్ ఉంచడానికి)
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
    bot.reply_to(message, "నమస్కారం! Pocket FM ఎపిసోడ్ లింక్ పంపండి, ఆడియో డౌన్‌లోడ్ చేసి ఇస్తాను.")

@bot.message_handler(func=lambda msg: True)
def download_audio(message):
    url = message.text.strip()
    chat_id = message.chat.id

    if "pocketfm" not in url:
        bot.reply_to(message, "దయచేసి సరైన Pocket FM లింక్ మాత్రమే పంపండి.")
        return

    wait_msg = bot.reply_to(message, "లింక్ విశ్లేషిస్తున్నాను... కొద్ది సెకన్లు ఆగండి.")

    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # షార్ట్ లింక్ రీడైరెక్ట్ ఫాలో అవ్వడం
        res = session.get(url, headers=headers, allow_redirects=True, timeout=25)
        html = res.text

        # ఆడియో URL కోసం విశ్లేషణ (.mp3 లేదా .m4a లేదా cdn లింక్స్)
        audio_urls = re.findall(r'https?://[^\s",\'<>]+\.(?:mp3|m4a)[^\s",\'<>]*', html)
        
        # ఒకవేళ డైరెక్ట్ లింక్ దొరకకపోతే JSON/Media లింక్స్ వెతకడం
        if not audio_urls:
            audio_urls = re.findall(r'https?://media[^\s",\'<>]+\.pocketfm[^\s",\'<>]+', html)

        if not audio_urls:
            bot.edit_message_text(
                "క్షమించండి, ఈ ఎపిసోడ్ ఆడియో దొరకలేదు. బ్రౌజర్‌లో ఓపెన్ చేసి డైరెక్ట్ స్టోరీ/ఎపిసోడ్ URL (ఉదా: pocketfm.com/show/...) పంపడానికి ప్రయత్నించండి.",
                chat_id=chat_id,
                message_id=wait_msg.message_id
            )
            return

        target_url = audio_urls[0]
        file_path = f"audio_{chat_id}_{message.message_id}.mp3"

        bot.edit_message_text("డౌన్‌లోడ్ పూర్తవుతోంది, టెలిగ్రామ్‌కు అప్‌లోడ్ చేస్తున్నాను...", 
                              chat_id=chat_id, message_id=wait_msg.message_id)

        audio_res = session.get(target_url, stream=True, timeout=90)
        with open(file_path, "wb") as f:
            for chunk in audio_res.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        with open(file_path, "rb") as audio:
            bot.send_audio(chat_id, audio, caption="మీ Pocket FM ఆడియో!")

        if os.path.exists(file_path):
            os.remove(file_path)

        bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"సమస్య వచ్చింది: {str(e)}", 
                              chat_id=chat_id, message_id=wait_msg.message_id)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling()
