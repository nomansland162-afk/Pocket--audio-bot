import os
import time
import threading
import subprocess
from flask import Flask
import telebot
import whisper

# 1. Railway Keep-Alive Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Seamless Audio Word Cutter Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot Configuration
BOT_TOKEN = "9193746618:AAHD9wKgTXligMSuGIKDmNm3PsTVArf5QdE"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# Whisper Model Load Cheyadam
print("Loading Whisper model...")
model = whisper.load_model("base")

user_data = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    text = (
        "🎙️ *Seamless Audio Word Remover Bot!*\n\n"
        "Audio nunchi unwanted word ni theesi audio flow miss avvakunda join chesthundhi:\n\n"
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

def get_audio_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(res.stdout.strip())

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
                    start_s = max(0.0, float(w["start"]) - 0.04)
                    end_s = float(w["end"]) + 0.04
                    intervals_to_cut.append((start_s, end_s))

        if not intervals_to_cut:
            bot.edit_message_text(
                f"ℹ️ Audio lo '{word_to_remove}' dorakaledu. Spelling check chesukoni malli type cheyandi.",
                chat_id=chat_id,
                message_id=status.message_id
            )
            return

        bot.edit_message_text(
            f"✂️ '{word_to_remove}' ({len(intervals_to_cut)} places lo) cut chesi smooth ga join chesthunnam...",
            chat_id=chat_id,
            message_id=status.message_id
        )

        total_dur = get_audio_duration(raw_audio_path)
        
        # 2. Segments split intervals calculate cheyadam
        kept_segments = []
        prev_end = 0.0
        for s_start, s_end in intervals_to_cut:
            if s_start > prev_end:
                kept_segments.append((prev_end, s_start))
            prev_end = max(prev_end, s_end)
            
        if prev_end < total_dur:
            kept_segments.append((prev_end, total_dur))

        # 3. FFmpeg tho prathi segment ni trim chesi merge cheyadam
        seg_files = []
        for idx, (st, en) in enumerate(kept_segments):
            dur = en - st
            if dur <= 0.05:
                continue
            seg_out = os.path.join(user_dir, f"part_{idx}.mp3")
            cmd = [
                "ffmpeg", "-y", "-ss", str(st), "-t", str(dur),
                "-i", raw_audio_path, "-c", "copy", seg_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(seg_out):
                seg_files.append(seg_out)

        # Segments list file
        concat_list = os.path.join(user_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for sf in seg_files:
                f.write(f"file '{os.path.abspath(sf)}'\n")

        clean_output_path = os.path.join(user_dir, "clean_audio.mp3")
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", clean_output_path
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 4. Clean audio send cheyadam
        with open(clean_output_path, 'rb') as af:
            bot.send_audio(
                chat_id=chat_id,
                audio=af,
                title="Seamless Clean Audio",
                caption=f"✅ '{word_to_remove}' word cut aipoindi! Continuous audio ready."
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
