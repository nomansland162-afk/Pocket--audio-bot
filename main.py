import os
import edge_tts
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telugu Voices
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

    try:
        chunks = [text[i:i+400] for i in range(0, len(text), 400)]
        audio_files = []

        for i, chunk in enumerate(chunks):
            communicate = edge_tts.Communicate(chunk, voice)
            file_name = f"temp_{user_id}_{i}.mp3"
            await communicate.save(file_name)
            audio_files.append(file_name)

        final_file = f"final_{user_id}.mp3"
        with open(final_file, "wb") as outfile:
            for f in audio_files:
                with open(f, "rb") as infile:
                    outfile.write(infile.read())
                os.remove(f)

        await update.message.reply_audio(
            audio=open(final_file, "rb"),
            title="Telugu Story",
            performer="TTS Bot"
        )

        os.remove(final_file)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error వచ్చింది: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(voice_callback))
    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, text_to_speech))

    print("Bot started...")
    app.run_polling()

if name == "main":
    main()
