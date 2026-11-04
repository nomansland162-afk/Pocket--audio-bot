import os
import re
import queue
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types
from eyed3 import load
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Pocket Downloader Clone is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y"
bot = telebot.TeleBot(BOT_TOKEN, num_threads=4)

try:
    bot.remove_webhook()
except Exception:
    pass

BRAND_NAME = "NRVA Network"
task_queue = queue.Queue()

# యూజర్ సేవ్ చేసిన స్టోరీస్ వివరాలు
user_saves = {}

# /start కమాండ్ - స్క్రీన్‌షాట్‌లో ఉన్న లేఅవుట్ ప్రకారం
@bot.message_handler(commands=['start'])
def start_cmd(message):
    first_name = message.from_user.first_name or "User"
    
    start_text = (
        f"🎧 *Welcome, {first_name}!* \n"
        "🔑 *Access: Free Trial Access*\n\n"
        "Here's what you can do:\n\n"
        "1️⃣ `/search` — find a story by name\n"
        "2️⃣ `/download` — paste a Pocket FM link / ID\n"
        "3️⃣ `/getlink` — convert an app link to a web link\n"
        "4️⃣ `/saves` — your saved stories\n"
        "5️⃣ `/free` — free 1-hour access\n"
        "6️⃣ `/subscribe` — unlock upcoming episodes\n"
        "7️⃣ `/storytv` — StoryTV video episodes\n\n"
        "💡 *Or just type a story name to search, or paste a link directly.*"
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_search = types.KeyboardButton("🔍 Search Story")
    btn_saves = types.KeyboardButton("📁 My Saves")
    markup.row(btn_search, btn_saves)
    
    bot.send_message(message.chat.id, start_text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['download'])
def download_instruction(message):
    bot.reply_to(message, "దయచేసి పాకెట్ ఎఫ్ఎం ఎపిసోడ్ లింక్ లేదా ఐడీని పేస్ట్ చేయండి.")

@bot.message_handler(commands=['search'])
def search_instruction(message):
    bot.reply_to(message, "మీరు వినాలనుకుంటున్న కథ పేరు టైప్ చేయండి (ఉదా: Yodha, Tiger Returns).")

@bot.message_handler(commands=['saves'])
def saves_cmd(message):
    chat_id = message.chat.id
    stories = user_saves.get(chat_id, [])
    if not stories:
        bot.reply_to(message, "📁 మీరు ఇంకా ఎలాంటి కథలను సేవ్ చేసుకోలేదు.")
    else:
        list_str = "\n".join([f"• {s}" for s in stories])
        bot.reply_to(message, f"📁 *Saved Stories:*\n\n{list_str}", parse_mode="Markdown")

@bot.message_handler(commands=['free'])
def free_cmd(message):
    bot.reply_to(message, "🎉 మీకు ఉచిత యాక్సెస్ యాక్టివేట్ చేయబడింది! లింక్స్ పంపి డౌన్‌లోడ్ చేసుకోవచ్చు.")

@bot.message_handler(commands=['subscribe'])
def sub_cmd(message):
    sub_text = (
        f"👑 *{BRAND_NAME} VIP Subscription*\n\n"
        "అన్ని లేటెస్ట్ ఎపిసోడ్స్ త్వరితగతిన పొందడానికి సబ్‌స్క్రిప్షన్ ప్లాన్స్:\n"
        "• 1 Month Access: ₹49\n"
        "• Lifetime Access: ₹99\n\n"
        "యాక్టివేషన్ కోసం అడ్మిన్‌ను సంప్రదించండి."
    )
    bot.reply_to(message, sub_text, parse_mode="Markdown")

# లింక్ నుండి ఆడియో సమాచారం గ్రాబ్ చేయడం
def download_audio_from_link(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        title = soup.title.string.strip() if soup.title else "Audio Track"
        title = title.split("|")[0].replace("Pocket FM", "").strip()
        
        audio_match = re.search(r'https?://[^\s"\'<>]+\.(?:mp3|m4a|aac)[^\s"\'<>]*', res.text)
        if audio_match:
            return audio_match.group(0), title
        return None, title
    except Exception:
        return None, "Audio Track"

# బ్యాక్‌గ్రౌండ్ క్యూ ప్రాసెసింగ్
def process_queue():
    while True:
        task = task_queue.get()
        if task is None:
            break
        
        chat_id, task_type, data, msg_id = task
        temp_file = f"audio_{chat_id}_{msg_id}.mp3"
        status_msg = bot.send_message(chat_id, "⏳ Fetching episode details... దయచేసి వేచి ఉండండి.")

        try:
            if task_type == "link":
                url = data
                media_url, clean_title = download_audio_from_link(url)
                
                if not media_url:
                    bot.edit_message_text("⚠️ ఆడియో స్ట్రీమ్ లింక్ లభించలేదు. నేరుగా ఆడియో ఫైల్‌ను ఫార్వర్డ్ చేయండి.",
                                          chat_id=chat_id, message_id=status_msg.message_id)
                    task_queue.task_done()
                    continue

                r = requests.get(media_url, stream=True, timeout=30)
                with open(temp_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            elif task_type == "file":
                file_id, file_name, orig_title, orig_performer = data
                clean_title = orig_title or file_name or "Audio Track"
                
                file_info = bot.get_file(file_id)
                downloaded = bot.download_file(file_info.file_path)
                with open(temp_file, 'wb') as f:
                    f.write(downloaded)

            found_nums = re.findall(r'\b\d+\b', clean_title)
            track_num = int(found_nums[0]) if found_nums else 1

            # ID3 ట్యాగ్స్ అప్‌డేట్
            try:
                audio_tag = load(temp_file)
                if audio_tag.tag is None:
                    audio_tag.initTag()
                audio_tag.tag.title = clean_title
                audio_tag.tag.artist = BRAND_NAME
                audio_tag.tag.album = BRAND_NAME
                audio_tag.tag.track_num = track_num
                audio_tag.tag.save()
            except Exception:
                pass

            # ఆడియో పంపడం
            with open(temp_file, 'rb') as final_audio:
                bot.send_audio(
                    chat_id=chat_id,
                    audio=final_audio,
                    title=clean_title,
                    performer=BRAND_NAME,
                    caption=f"🎧 *{clean_title}*\n🔥 Powered by *{BRAND_NAME}*",
                    parse_mode="Markdown"
                )

            bot.delete_message(chat_id, status_msg.message_id)

        except Exception as err:
            bot.edit_message_text(f"Error: {str(err)}", chat_id=chat_id, message_id=status_msg.message_id)

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            task_queue.task_done()

# లింక్స్ హ్యాండ్లింగ్
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("http"))
def handle_link(message):
    task_queue.put((message.chat.id, "link", message.text.strip(), message.message_id))

# ఆడియో ఫైల్స్ హ్యాండ్లింగ్
@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    file_id = None
    file_name = ""
    orig_title = ""
    orig_performer = ""

    if message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or ""
        orig_title = message.audio.title or ""
        orig_performer = message.audio.performer or ""
    elif message.document and message.document.mime_type and "audio" in message.document.mime_type:
        file_id = message.document.file_id
        file_name = message.document.file_name or ""
    else:
        return

    data = (file_id, file_name, orig_title, orig_performer)
    task_queue.put((message.chat.id, "file", data, message.message_id))

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=process_queue, daemon=True).start()
    bot.infinity_polling(skip_pending=True, timeout=20)
