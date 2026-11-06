if not intervals_to_cut:
            bot.edit_message_text(
                f"ℹ️ Audio lo '{word_to_remove}' dorakaledu. Spelling check chesukoni malli type cheyandi.",
                chat_id=chat_id,
                message_id=status.message_id
            )
            return

        bot.edit_message_text(
            f"✂️ '{word_to_remove}' ({len(intervals_to_cut)} sarlu) cut chesi, audio ni smooth ga join chesthunnam...",
            chat_id=chat_id,
            message_id=status.message_id
        )

        # 2. Seamless splice & smooth crossfade
        sound = AudioSegment.from_file(raw_audio_path)
        
        # Audio pieces ni extract cheyadam
        kept_pieces = []
        prev_end = 0
        
        for start_ms, end_ms in intervals_to_cut:
            if start_ms > prev_end:
                kept_pieces.append(sound[prev_end:start_ms])
            prev_end = max(prev_end, end_ms)
            
        if prev_end < len(sound):
            kept_pieces.append(sound[prev_end:])

        # Pieces anni smoothly kalapadam (crossfade tho pop/click sound raకుండా)
        final_sound = kept_pieces[0]
        for piece in kept_pieces[1:]:
            if len(final_sound) > 30 and len(piece) > 30:
                final_sound = final_sound.append(piece, crossfade=25)
            else:
                final_sound = final_sound + piece

        clean_output_path = os.path.join(user_dir, "clear_cut_audio.mp3")
        final_sound.export(clean_output_path, format="mp3", bitrate="192k")

        # 3. Output send cheyadam
        with open(clean_output_path, 'rb') as af:
            bot.send_audio(
                chat_id=chat_id,
                audio=af,
                title="Seamless Cleaned Audio",
                caption=f"✅ '{word_to_remove}' word ni cut chesi continuous audio ready chesam!"
            )

        bot.delete_message(chat_id, status.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error vachindi: {str(e)}", chat_id=chat_id, message_id=status.message_id)

    finally:
        if chat_id in user_data:
            del user_data[chat_id]

if name == "main":
    threading.Thread(target=run_web, daemon=True).start()
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    bot.infinity_polling(timeout=15, long_polling_timeout=10)
