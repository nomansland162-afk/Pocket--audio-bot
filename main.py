import os
import time
import threading
from flask import Flask
import telebot
import whisper
from pydub import AudioSegment

# 1. Railway Keep-Alive Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Seamless Audio Word Cutter Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot Configuration
BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# Whisper Model Load Cheyadam
print("Loading Whisper model...")
model = whisper.load_model("base")

user_data = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    text = (
        "🎙️ *Seamless Audio Word Remover Bot!*\n\n"
        "Audio nunchi unwanted word ni theesi smooth ga kaluputhundi:\n\n"
        "1. Mundu oka **Audio** leda **Voice Note** pampandi.\n"
        "2. Tarvata e audio lo ye word theeseyalo aa word ni type cheyandi.\n"
        "3. Bot aa word ni cut chesi clean continuous audio ni pampisthundi!"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['audio', 'voice', 'document'])
def handle_audio(message):
    chat_id = message.chat.id
    
    file_id = None
    if message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id
    elif message.document and message.document.mime_type and "audio" in message.document.mime_type:
        file_id = message.document.file_id

    if not file_id:
        bot.reply_to(message, "Dayachesi valid audio file pampandi.")
        return

    status = bot.reply_to(message, "⏳ Audio download chesthunnam... Dayachesi aagandi.")
    
    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = f"temp_{chat_id}_{int(time.time())}"
        os.makedirs(user_dir, exist_ok=True)
        raw_path = os.path.join(user_dir, "input_audio.mp3")
        
        with open(raw_path, 'wb') as f:
            f.write(downloaded)
            
        user_data[chat_id] = {
            "dir": user_dir,
            "raw_audio": raw_path
        }
        
        bot.edit_message_text(
            "✅ Audio receive aindi!\n\nIppudu e audio nunchi **ye word theeseyalo** aa word ni type chesi message ga pampandi:",
            chat_id=chat_id,
            message_id=status.message_id
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error vachindi: {str(e)}",
            chat_id=chat_id,
            message_id=status.message_id
        )

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/'))
def process_word_cut(message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or "raw_audio" not in user_data[chat_id]:
        bot.reply_to(message, "Mundu audio file pampandi mava, tarvata word type cheyandi!")
        return

    word_to_remove = message.text.strip().lower()
    raw_audio_path = user_data[chat_id]["raw_audio"]
    user_dir = user_data[chat_id]["dir"]

    status = bot.reply_to(message, f"🔍 Audio lo '{word_to_remove}' word timestamps kanukkuntunnam...")

    try:
        # 1. Whisper dwara word level timestamps extract cheyadam
        result = model.transcribe(raw_audio_path, word_timestamps=True)
        
        intervals_to_cut = []
        for segment in result.get("segments", []):
            for w in segment.get("words", []):
                cleaned_w = w["word"].strip().lower()
                cleaned_w = "".join([ch for ch in cleaned_w if ch.isalnum()])
                if cleaned_w == word_to_remove:
                    start_ms = max(0, int(w["start"] * 1000) - 35)
                    end_ms = int(w["end"] * 1000) + 35
                    intervals_to_cut.append((start_ms, end_ms))

        if not intervals_to_cut:
            bot.edit_message_text(
                f"ℹ️ Audio lo '{word_to_remove}' dorakaledu. Spelling check chesukoni malli type cheyandi.",
                chat_id=chat_id,
                message_id=status.message_id
            )
            return

        bot.edit_message_text(
            f"✂️ '{word_to_remove}' ({len(intervals_to_cut)} sarlu) cut chesi smooth ga join chesthunnam...",
            chat_id=chat_id,
            message_id=status.message_id
        )

        # 2. AudioSegment tho seamless cut & crossfade
        sound = AudioSegment.from_file(raw_audio_path)
        
        kept_pieces = []
        prev_end = 0
        for start_ms, end_ms in intervals_to_cut:
            if start_ms > prev_end:
                kept_pieces.append(sound[prev_end:start_ms])
            prev_end = max(prev_end, end_ms)
            
        if prev_end < len(sound):
            kept_pieces.append(sound[prev_end:])

        final_sound = kept_pieces[0]
        for piece in kept_pieces[1:]:
            if len(final_sound) > 30 and len(piece) > 30:
                final_sound = final_sound.append(piece, crossfade=20)
            else:
                final_sound = final_sound + piece

        clean_output_path = os.path.join(user_dir, "clear_cut_audio.mp3")
        final_sound.export(clean_output_path, format="mp3", bitrate="192k")

        # 3. Clean audio send cheyadam
        with open(clean_output_path, 'rb') as af:
            bot.send_audio(
                chat_id=chat_id,
                audio=af,
                title="Seamless Clean Audio",
                caption=f"✅ '{word_to_remove}' cut aipoindi! Continuous audio ready."
            )

        bot.delete_message(chat_id, status.message_id)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Error vachindi: {str(e)}",
            chat_id=chat_id,
            message_id=status.message_id
        )

    finally:
        if chat_id in user_data:
            del user_data[chat_id]

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    bot.infinity_polling(timeout=15, long_polling_timeout=10)
