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

VOICES = {
    "female": "te-IN-ShrutiNeural",
    "male": "te-IN-MohanNeural"
}

# User preferences store cheyadam: voice, rate, pitch
user_settings = {}

def get_user_config(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            "voice": "male",
            "rate": "-8%",
            "pitch": "-6Hz"
        }
    return user_settings[chat_id]

def get_settings_markup(chat_id):
    cfg = get_user_config(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Voice selection
    v_f = "✅ Female" if cfg["voice"] == "female" else "Female"
    v_m = "✅ Male" if cfg["voice"] == "male" else "Male"
    btn_f = types.InlineKeyboardButton(f"👩 {v_f}", callback_data="set_v_female")
    btn_m = types.InlineKeyboardButton(f"👨 {v_m}", callback_data="set_v_male")
    
    # Speed selection
    r_slow = "✅ Slow" if cfg["rate"] == "-15%" else "Slow (-15%)"
    r_med = "✅ Drama" if cfg["rate"] == "-8%" else "Drama (-8%)"
    r_norm = "✅ Normal" if cfg["rate"] == "+0%" else "Normal (0%)"
    btn_r1 = types.InlineKeyboardButton(r_slow, callback_data="set_r_-15%")
    btn_r2 = types.InlineKeyboardButton(r_med, callback_data="set_r_-8%")
    btn_r3 = types.InlineKeyboardButton(r_norm, callback_data="set_r_+0%")
    
    # Pitch (Bass) selection
    p_deep = "✅ Deep Bass" if cfg["pitch"] == "-10Hz" else "Deep Bass (-10Hz)"
    p_drama = "✅ Dramatic" if cfg["pitch"] == "-6Hz" else "Dramatic (-6Hz)"
    p_norm = "✅ Normal" if cfg["pitch"] == "+0Hz" else "Normal (0Hz)"
    btn_p1 = types.InlineKeyboardButton(p_deep, callback_data="set_p_-10Hz")
    btn_p2 = types.InlineKeyboardButton(p_drama, callback_data="set_p_-6Hz")
    btn_p3 = types.InlineKeyboardButton(p_norm, callback_data="set_p_+0Hz")
    
    markup.add(btn_f, btn_m)
    markup.add(btn_r1, btn_r2, btn_r3)
    markup.add(btn_p1, btn_p2, btn_p3)
    return markup

@bot.message_handler(commands=['start', 'settings'])
def settings_cmd(message):
    chat_id = message.chat.id
    cfg = get_user_config(chat_id)
    
    text = (
        "🎙 *Telugu Audio Story Settings*\n\n"
        f"• *Voice:* {cfg['voice'].capitalize()}\n"
        f"• *Speed (Rate):* {cfg['rate']}\n"
        f"• *Pitch (Bass):* {cfg['pitch']}\n\n"
        "Meeku kavalsina settings kinda buttons tho select cheskoni, direct ga Story text pampandi:"
    )
    bot.send_message(chat_id, text, reply_markup=get_settings_markup(chat_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_update(call):
    chat_id = call.message.chat.id
    cfg = get_user_config(chat_id)
    
    action = call.data.split("_")
    category = action[1]
    value = action[2]
    
    if category == "v":
        cfg["voice"] = value
    elif category == "r":
        cfg["rate"] = value
    elif category == "p":
        cfg["pitch"] = value
        
    bot.answer_callback_query(call.id, text="Settings Updated!")
    
    text = (
        "🎙 *Telugu Audio Story Settings*\n\n"
        f"• *Voice:* {cfg['voice'].capitalize()}\n"
        f"• *Speed (Rate):* {cfg['rate']}\n"
        f"• *Pitch (Bass):* {cfg['pitch']}\n\n"
        "Meeku kavalsina settings kinda buttons tho select cheskoni, direct ga Story text pampandi:"
    )
    bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_settings_markup(chat_id), parse_mode="Markdown")

async def generate_edge_audio(text, voice_id, rate_val, pitch_val, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_id,
        rate=rate_val,
        pitch=pitch_val
    )
    await communicate.save(output_path)

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/'))
def convert_to_audio(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if len(text) < 5:
        bot.reply_to(message, "Dayachesi konchem pedda katha text pampandi.")
        return

    cfg = get_user_config(chat_id)
    voice_id = VOICES[cfg["voice"]]
    rate_val = cfg["rate"]
    pitch_val = cfg["pitch"]

    status_msg = bot.reply_to(message, "⏳ Audio tayaravuthondi... Dayachesi wait cheyandi.")
    temp_file = f"story_{chat_id}_{message.message_id}.mp3"

    try:
        asyncio.run(generate_edge_audio(text, voice_id, rate_val, pitch_val, temp_file))

        performer_tag = f"{cfg['voice'].capitalize()} ({rate_val}, {pitch_val})"

        with open(temp_file, 'rb') as audio_fp:
            bot.send_audio(
                chat_id=chat_id,
                audio=audio_fp,
                title="Telugu Audio Story",
                performer=performer_tag
            )

        bot.delete_message(chat_id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error vachindi: {str(e)}", chat_id=chat_id, message_id=status_msg.message_id)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    bot.infinity_polling(timeout=10, long_polling_timeout=5)
