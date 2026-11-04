import os
import re
import subprocess
import telebot
from eyed3 import load
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Tag Editor & 2x Speed Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGiZH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN)

user_settings = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user_settings[chat_id] = {"count": 1, "story": "YODHA", "speed": "2.0"}
    bot.reply_to(message, "Bot ready! Audio files ni automatic ga 2x speed tho convert chesi serial order lo tags vestundi.")

@bot.message_handler(commands=['setstory'])
def set_story(message):
    chat_id = message.chat.id
    title = message.text.replace("/setstory", "").strip()
    if title:
        if chat_id not in user_settings:
            user_settings[chat_id] = {"count": 1, "speed": "2.0"}
        user_settings[chat_id]["story"] = title
        bot.reply_to(message, f"Story Name: {title}")

@bot.message_handler(commands=['setep'])
def set_ep(message):
    chat_id = message.chat.id
    try:
        val = int(message.text.replace("/setep", "").strip())
        if chat_id not in user_settings:
            user_settings[chat_id] = {"story": "YODHA", "speed": "2.0"}
        user_settings[chat_id]["count"] = val
        bot.reply_to(message, f"Next Episode: {val}")
    except:
        bot.reply_to(message, "Correct number ivvandi. Ex: /setep 1")

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    chat_id = message.chat.id
    file_id = None
    original_name = ""

    if message.audio:
        file_id = message.audio.file_id
        original_name = message.audio.file_name or message.audio.title or ""
    elif message.document and message.document.mime_type and "audio" in message.document.mime_type:
        file_id = message.document.file_id
        original_name = message.document.file_name or ""
    else:
        return

    if chat_id not in user_settings:
        user_settings[chat_id] = {"count": 1, "story": "YODHA", "speed": "2.0"}

    story_name = user_settings[chat_id]["story"]

    # File name lo number unte adhe teesukuntundi (Order miss avvakunda)
    found_nums = re.findall(r'\b\d+\b', original_name)
    if found_nums:
        ep_num = int(found_nums[0])
    else:
        ep_num = user_settings[chat_id]["count"]
        user_settings[chat_id]["count"] += 1

    status_msg = bot.reply_to(message, f"Converting Ep {ep_num:02d} to 2x speed...")

    raw_input = f"raw_{chat_id}_{message.message_id}.mp3"
    speed_output = f"speed_{chat_id}_{message.message_id}.mp3"

    try:
        # Download
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(raw_input, 'wb') as f:
            f.write(downloaded)

        # 2x Speed conversion using FFmpeg
        cmd = f'ffmpeg -y -i "{raw_input}" -filter:a "atempo=2.0" -vn "{speed_output}"'
        subprocess.run(cmd, shell=True, check=True)

        # Tags Editing
        formatted_title = f"{story_name} - Episode {ep_num:02d}"
        try:
            audio_tag = load(speed_output)
            if audio_tag.tag is None:
                audio_tag.initTag()
            audio_tag.tag.title = formatted_title
            audio_tag.tag.artist = story_name
            audio_tag.tag.album = story_name
            audio_tag.tag.track_num = ep_num
            audio_tag.tag.save()
        except Exception:
            pass

        # Send 2x Audio
        with open(speed_output, 'rb') as final_audio:
            bot.send_audio(
                chat_id=chat_id,
                audio=final_audio,
                title=formatted_title,
                performer=story_name,
                caption=f"⚡ {story_name} - Ep {ep_num:02d} (2x Speed)"
            )

        bot.delete_message(chat_id, status_msg.message_id)

    except Exception as err:
        bot.edit_message_text(f"Error: {str(err)}", chat_id=chat_id, message_id=status_msg.message_id)

    finally:
        if os.path.exists(raw_input):
            os.remove(raw_input)
        if os.path.exists(speed_output):
            os.remove(speed_output)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
