import os
import edge_tts
import asyncio
import threading
from flask import Flask
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 1. Railway Keep-Alive సర్వర్
server = Flask(__name__)

@server.route('/')
def home():
    return "Telugu TTS Bot is Running Live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# 2. బాట్ కాన్ఫిగరేషన్
BOT_TOKEN = "9089667063:AAGiLVW9zdSWuqyTn1YMeTAcGIzH6B-YP-Y"

VOICES = {
    "female": "te-IN-ShrutiNeural",
    "male": "te-IN-MohanNeural"
}

user_voices = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("👩 Female Voice", callback_data="voice_female"),
            InlineKeyboardButton("👨 Male Voice", callback_data="voice_male")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "నమస్కారం! 👋\n\n"
        "నేను Telugu Story ని Audio గా మార్చే Bot.\n\n"
        "ముందుగా Voice select చేసుకోండి:",
        reply_markup=reply_markup
    )

async def voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if query.data == "voice_female":
        user_voices[user_id] = "female"
        await query.edit_message_text("✅ Female voice select చేశారు.\n\nఇప్పుడు మీ Story text పంపండి.")
    else:
        user_voices[user_id] = "male"
        await query.edit_message_text("✅ Male voice select చేశారు.\n\nఇప్పుడు మీ Story text పంపండి.")

async def text_to_speech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if len(text) < 10:
        await update.message.reply_text("దయచేసి కాస్త పొడవైన story పంపండి.")
        return

    voice_type = user_voices.get(user_id, "female")
    voice = VOICES[voice_type]

    msg = await update.message.reply_text("⏳ Audio create అవుతోంది... దయచేసి wait చేయండి.")

    final_file = f"final_{user_id}.mp3"

    try:
        # Edge TTS ట్రై చేయడం
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(final_file)
    except Exception:
        # Edge TTS సర్వర్ 403 ఇస్తే ఆటోమేటిక్‌గా gTTS బ్యాకప్ వాడుతుంది
        try:
            tts = gTTS(text=text, lang='te')
            tts.save(final_file)
        except Exception as gtts_err:
            await msg.edit_text(f"❌ Error వచ్చింది: {str(gtts_err)}")
            return

    try:
        with open(final_file, "rb") as audio_fp:
            await update.message.reply_audio(
                audio=audio_fp,
                title="Telugu Story",
                performer="STORYMAX"
            )

        if os.path.exists(final_file):
            os.remove(final_file)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error వచ్చింది: {str(e)}")

def main():
    # Flask ను బ్యాక్‌గ్రౌండ్ థ్రెడ్‌లో నడపడం
    threading.Thread(target=run_flask, daemon=True).start()

    # బాట్ అప్లికేషన్ స్టార్ట్ చేయడం
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(voice_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_to_speech))

    print("Bot is starting...")
    application.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
