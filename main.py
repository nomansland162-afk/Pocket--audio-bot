import os
import asyncio
import threading
from flask import Flask
import telebot
from telebot import types
import edge_tts

# 1. Railway Keep-Alive సర్వర్
app = Flask(__name__)

@app.route('/')
def home():
    return "STORYMAX Male/Female TTS Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. టెలిగ్రామ్ బాట్ సెటప్
BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

try:
    bot.remove_webhook()
except Exception:
    pass

# తెలుగు వాయిస్‌లు
VOICES = {
    "female": "te-IN-ShrutiNeural",
    "male": "te-IN-MohanNeural"
}

user_selected_voice = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    welcome_text = (
        "నమస్కారం! 👋\n\n"
        "నేను తెలుగు కథలను ఆడియోగా మార్చే బాట్.\n\n"
        "మీకు ఏ గొంతులో కథ కావాలో క్రింది బటన్ ద్వారా ఎంచుకోండి:"
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
    bot.send_message(chat_id, f"✅ మీరు *{voice_name}* ఎంచుకున్నారు.\n\nఇప్పుడు మీ తెలుగు స్టోరీ టెక్స్ట్‌ను ఇక్కడ మెసేజ్ పంపండి.", parse_mode="Markdown")

async def generate_edge_audio(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/'))
def convert_to_audio(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if len(text) < 5:
        bot.reply_to(message, "దయచేసి కాస్త పొడవైన కథ టెక్స్ట్ పంపండి.")
        return

    # యూజర్ వాయిస్ ఎంచుకోకపోతే డీఫాల్ట్‌గా ఫిమేల్ వాయిస్ సెట్ అవుతుంది
    chosen_type = user_selected_voice.get(chat_id, "female")
    voice_id = VOICES[chosen_type]

    status_msg = bot.reply_to(message, "⏳ ఆడియో తయారవుతోంది... దయచేసి ఒక్క క్షణం ఆగండి.")
    temp_file = f"story_{chat_id}_{message.message_id}.mp3"

    try:
        # Edge TTS ఆడియో జనరేట్ చేయడం
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
        bot.edit_message_text(f"❌ Error వచ్చింది: {str(e)}", chat_id=chat_id, message_id=status_msg.message_id)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
