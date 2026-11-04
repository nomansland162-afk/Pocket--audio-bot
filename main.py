import os
import asyncio
import threading
from flask import Flask
import telebot
from telebot import types
import edge_tts

# 1. Railway Keep-Alive Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "STORYMAX TTS Bot is Running Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot Configuration
BOT_TOKEN = "9208695742:AAH98SOyNqAE0DWEIqBmNUusOSjMogUXESs"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# Telugu Voices
VOICES = {
    "female": "te-IN-ShrutiNeural",
    "male": "te-IN-MohanNeural"
}

user_selected_voice = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    welcome_text = (
        "Namaskaram! 👋\n\n"
        "Nenu Telugu Story ni Audio ga marche Bot.\n\n"
        "Meeku ye voice lo katha kavalo kinda unna button click chesi select cheskondi:"
    )
    markup = types.InlineKeyboardMarkup()
    btn_female = types.InlineKeyboardButton("👩 Female Voice (Shruti)", callback_data="voice_female")
    btn_male = types.InlineKeyboardButton("👨 Male Voice (Mohan)", callback_data="voice_male")
    markup.add(btn_female, btn_male)

    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("voice_"))
def handle_voice_selection(call):
    chat_id = call.message.chat.id
    selected = call.data.replace("voice_", "")
    user_selected_voice[chat_id] = selected
    
    bot.answer_callback_query(call.id)
    voice_name = "👩 Female Voice (Shruti)" if selected == "female" else "👨 Male Voice (Mohan)"
    bot.send_message(
        chat_id, 
        f"✅ Meeru *{voice_name}* select cheskunnaru.\n\nIppudu mee Telugu story text ni ikkada message pampandi.", 
        parse_mode="Markdown"
    )

async def generate_edge_audio(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/'))
def convert_to_audio(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if len(text) < 5:
        bot.reply_to(message, "Dayachesi konchem pedda katha text pampandi.")
        return

    # User voice select cheskokapothe default ga Female voice vasthundi
    chosen_type = user_selected_voice.get(chat_id, "female")
    voice_id = VOICES[chosen_type]

    status_msg = bot.reply_to(message, "⏳ Audio tayaravuthondi... Dayachesi oka kshanam aagandi.")
    temp_file = f"story_{chat_id}_{message.message_id}.mp3"

    try:
        # Edge TTS dwara audio create cheyadam
        asyncio.run(generate_edge_audio(text, voice_id, temp_file))

        performer_title = "Female Voice (Shruti)" if chosen_type == "female" else "Male Voice (Mohan)"

        with open(temp_file, 'rb') as audio_fp:
            bot.send_audio(
                chat_id=chat_id,
                audio=audio_fp,
                title="Telugu Audio Story",
                performer=performer_title
            )

        bot.delete_message(chat_id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error vachindi: {str(e)}", chat_id=chat_id, message_id=status_msg.message_id)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    # Railway keep-alive web server background thread lo run avthundi
    threading.Thread(target=run_web, daemon=True).start()
    
    # Patha polling conflicts emaina unte clear cheyadam
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    # Bot uninterrupted infinity polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
