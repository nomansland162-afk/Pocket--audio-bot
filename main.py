import os
import re
import requests
import telebot

# ఇక్కడ మీ BotFather నుండి వచ్చిన Token ని పేస్ట్ చేయండి
BOT_TOKEN = "ఇక్కడ_మీ_TOKEN_రాయండి"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_msg(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, f"నమస్కారం {user_name}! Pocket FM ఎపిసోడ్ లింక్ ఇక్కడ పంపండి, ఆడియో డౌన్‌లోడ్ చేసి ఇస్తాను.")

@bot.message_handler(func=lambda msg: True)
def download_audio(message):
    url = message.text.strip()
    chat_id = message.chat.id

    if "pocketfm" not in url:
        bot.reply_to(message, "దయచేసి సరైన Pocket FM లింక్ మాత్రమే పంపండి.")
        return

    wait_msg = bot.reply_to(message, "ఆడియో లింక్ కోసం చూస్తున్నాను... కాసేపు వేచి ఉండండి.")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36'
        }
        res = requests.get(url, headers=headers, timeout=20)
        html = res.text

        # పేజీలోని ఆడియో స్ట్రీమ్ లేదా mp3 లింక్ వెతకడం
        audio_urls = re.findall(r'https?://[^\s",\']+\.mp3[^\s",\']*', html)

        if not audio_urls:
            bot.edit_message_text(
                "క్షమించండి, ఈ ఆడియోను తీయలేకపోయాను (ఇది లాక్ చేయబడిన ప్రీమియం ఎపిసోడ్ కావచ్చు).",
                chat_id=chat_id,
                message_id=wait_msg.message_id
            )
            return

        target_url = audio_urls[0]
        # ప్రతి యూజర్ కోసం సపరేట్ ఫైల్ నేమ్
        file_path = f"audio_{chat_id}_{message.message_id}.mp3"

        bot.edit_message_text("డౌన్‌లోడ్ పూర్తవుతోంది, టెలిగ్రామ్‌కు అప్‌లోడ్ చేస్తున్నాను...", 
                              chat_id=chat_id, message_id=wait_msg.message_id)

        # ఆడియోను సర్వర్‌లోకి డౌన్‌లోడ్ చేయడం
        audio_res = requests.get(target_url, stream=True, timeout=60)
        with open(file_path, "wb") as f:
            for chunk in audio_res.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        # యూజర్‌కు ఆడియో పంపడం
        with open(file_path, "rb") as audio:
            bot.send_audio(chat_id, audio, caption="మీ ఆడియో సిద్ధమైంది!")

        # సర్వర్‌లో మెమరీ నిండకుండా ఫైల్ డిలీట్ చేయడం
        if os.path.exists(file_path):
            os.remove(file_path)

        bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"సమస్య వచ్చింది: {str(e)}", 
                              chat_id=chat_id, message_id=wait_msg.message_id)

bot.infinity_polling()
