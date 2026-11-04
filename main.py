import os
import re
import queue
import threading
import telebot
from eyed3 import load
from flask import Flask

# Flask keep-alive web server
app = Flask(__name__)

@app.route('/')
def home():
    return "Original Audio Tag Editor is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.remove_webhook()
except Exception:
    pass

user_settings = {}
# Order miss avvakunda okadanitharvatha okati process cheyadaniki Queue
task_queue = queue.Queue()

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user_settings[chat_id] = {"count": 1, "story": "YODHA"}
    bot.reply_to(message, "🎧 *Batch Episode Organizer Ready!*\n\n"
                          "1. Katha peru marchadaniki: `/setstory YODHA`\n"
                          "2. Start number set cheyadaniki: `/setep 1`\n\n"
                          "Audio files ni pampandi, original quality lo orderwise serial ga tags vesi pampisthanu.",
                 parse_mode="Markdown")

@bot.message_handler(commands=['setstory'])
def set_story(message):
    chat_id = message.chat.id
    title = message.text.replace("/setstory", "").strip()
    if title:
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
            user_settings[chat_id] = {"story": "YODHA"}
        user_settings[chat_id]["count"] = val
        bot.reply_to(message, f"✅ Next Episode number: *{val}*", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Correct number ivvandi. Ex: `/setep 1`", parse_mode="Markdown")

# Worker thread: Files ni line ga oka order lo process chesthundi
def process_queue():
    while True:
        task = task_queue.get()
        if task is None:
            break
        
        chat_id, file_id, original_name, msg_id = task
        if chat_id not in user_settings:
            user_settings[chat_id] = {"count": 1, "story": "YODHA"}

        story_name = user_settings[chat_id]["story"]

        # File name lo number unte direct ga adhe number theeskuntundi (Order miss avvadu)
        found_nums = re.findall(r'\b\d+\b', original_name)
        if found_nums:
            ep_num = int(found_nums[0])
        else:
            ep_num = user_settings[chat_id]["count"]
            user_settings[chat_id]["count"] += 1

        status_msg = bot.send_message(chat_id, f"Processing Ep {ep_num}...")

        temp_file = f"audio_{chat_id}_{msg_id}.mp3"

        try:
            # File download
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(temp_file, 'wb') as f:
                f.write(downloaded)

            formatted_title = f"{story_name} - Episode {ep_num:02d}"

            # Original file meeda direct ga tags edit cheyadam (No conversion, 100% original quality)
            try:
                audio_tag = load(temp_file)
                if audio_tag.tag is None:
                    audio_tag.initTag()
                audio_tag.tag.title = formatted_title
                audio_tag.tag.artist = story_name
                audio_tag.tag.album = story_name
                audio_tag.tag.track_num = ep_num
                audio_tag.tag.save()
            except Exception:
                pass

            # Send original audio back
            with open(temp_file, 'rb') as final_audio:
                bot.send_audio(
                    chat_id=chat_id,
                    audio=final_audio,
                    title=formatted_title,
                    performer=story_name,
                    caption=f"🎬 *{story_name}*\n🎧 Episode: *{ep_num:02d}*",
                    parse_mode="Markdown"
                )

            bot.delete_message(chat_id, status_msg.message_id)

        except Exception as err:
            bot.edit_message_text(f"Error: {str(err)}", chat_id=chat_id, message_id=status_msg.message_id)

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            task_queue.task_done()

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

    # Queue lo pettadam valla anni files varasaga line lo process avthayi
    task_queue.put((chat_id, file_id, original_name, message.message_id))

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=process_queue, daemon=True).start()
    bot.infinity_polling(skip_pending=True, timeout=20)
