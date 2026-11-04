import os
import telebot
from eyed3 import load
from threading import Thread
from flask import Flask

# Web server Railway lo active ga undadaniki
app = Flask(__name__)

@app.route('/')
def home():
    return "Tag Editor Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Mee Bot Token
BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGiZH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN)

# User session data (Episode count track cheyadaniki)
user_settings = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user_settings[chat_id] = {"count": 1, "story": "Audio Drama"}
    welcome_text = (
        "🎧 *Batch Episode Renamer & Tag Editor Bot*\n\n"
        "Mee audio files ni serial order lo set cheyadaniki ivi use cheyandi:\n"
        "1. Story Name set cheyandi: `/setstory Katha Peru`\n"
        "2. Starting Episode Number set cheyandi: `/setep 1`\n"
        "3. Ep count malli reset cheyadaniki: `/reset`\n\n"
        "Settings set chesaka audio files ni varasaga (1, 2, 3...) forward cheyandi."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['setstory'])
def set_story(message):
    chat_id = message.chat.id
    title = message.text.replace("/setstory", "").strip()
    if not title:
        bot.reply_to(message, "Katha peru ivvandi. Ex: `/setstory 21 Universe`", parse_mode="Markdown")
        return
    if chat_id not in user_settings:
        user_settings[chat_id] = {"count": 1}
    user_settings[chat_id]["story"] = title
    bot.reply_to(message, f"✅ Story Name set ayindi: *{title}*", parse_mode="Markdown")

@bot.message_handler(commands=['setep'])
def set_ep(message):
    chat_id = message.chat.id
    try:
        val = int(message.text.replace("/setep", "").strip())
        if chat_id not in user_settings:
            user_settings[chat_id] = {"story": "Audio Drama"}
        user_settings[chat_id]["count"] = val
        bot.reply_to(message, f"✅ Next Episode number: *{val}*", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Correct number ivvandi. Ex: `/setep 1`", parse_mode="Markdown")

@bot.message_handler(commands=['reset'])
def reset_counter(message):
    chat_id = message.chat.id
    if chat_id in user_settings:
        user_settings[chat_id]["count"] = 1
    bot.reply_to(message, "Counter reset ayindi. Next episode: *1*", parse_mode="Markdown")

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    chat_id = message.chat.id
    
    # Audio or MP3 document check
    file_id = None
    if message.audio:
        file_id = message.audio.file_id
    elif message.document and message.document.mime_type and "audio" in message.document.mime_type:
        file_id = message.document.file_id
    else:
        bot.reply_to(message, "Dayachesi MP3 audio file mathrame pampandi.")
        return

    if chat_id not in user_settings:
        user_settings[chat_id] = {"count": 1, "story": "Audio Drama"}

    ep_num = user_settings[chat_id]["count"]
    story_name = user_settings[chat_id]["story"]

    status_msg = bot.reply_to(message, f"Processing Episode {ep_num}...")

    try:
        # File Download
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        temp_input = f"input_{chat_id}.mp3"
        with open(temp_input, 'wb') as f:
            f.write(downloaded)

        # ID3 Tags Editing
        formatted_title = f"{story_name} - Episode {ep_num:02d}"
        
        try:
            audio_tag = load(temp_input)
            if audio_tag.tag is None:
                audio_tag.initTag()
            audio_tag.tag.title = formatted_title
            audio_tag.tag.artist = story_name
            audio_tag.tag.album = story_name
            audio_tag.tag.track_num = ep_num
            audio_tag.tag.save()
        except Exception:
            pass

        # Send Modified Audio
        with open(temp_input, 'rb') as final_file:
            bot.send_audio(
                chat_id=chat_id,
                audio=final_file,
                title=formatted_title,
                performer=story_name,
                caption=f"🎬 *{story_name}*\n🎧 Episode: *{ep_num:02d}*",
                parse_mode="Markdown"
            )

        # Cleanup & Increment
        if os.path.exists(temp_input):
            os.remove(temp_input)

        user_settings[chat_id]["count"] += 1
        bot.delete_message(chat_id, status_msg.message_id)

    except Exception as err:
        bot.edit_message_text(f"Error: {str(err)}", chat_id=chat_id, message_id=status_msg.message_id)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
