
import logging
import asyncio
import os
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from config import TELEGRAM_TOKEN, validate_env

from services.audio_service import AudioService
from services.gemini_service import GeminiService
from services.db_service import DBService
from keep_alive import keep_alive

# Validate environment before starting
validate_env()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Services
audio_service = AudioService()
gemini_service = GeminiService()
db_service = DBService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and the FIRST LESSON."""
    user = update.effective_user
    db_service.update_user(user.id, user.username, user.first_name)
    
    # 1. Welcome Text
    welcome_text = (
        "👋 ¡Hola! Soy tu K-Voice Coach.\n"
        "Veo que estás empezando, así que **yo te guiaré paso a paso**.\n\n"
        "🎯 **Lección 1: El Saludo**\n"
        "Escucha mi audio y **repite conmigo**:"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)
    
    # 2. First Lesson Audio (Proactive teaching)
    first_lesson_text = "안녕하세요" # Annyeonghaseyo
    tts_filename = f"lesson1_{user.id}.mp3"
    
    lesson_caption = (
        "🇰🇷 **안녕하세요**\n"
        "🔤 Annyeonghaseyo\n"
        "📖 *An-ñong-ha-se-yo*\n"
        "🇪🇸 Hola"
    )

    try:
        tts_path = await audio_service.generate_tts(first_lesson_text, output_file=tts_filename)
        await context.bot.send_voice(
            chat_id=update.effective_chat.id, 
            voice=open(tts_path, 'rb'),
            caption=lesson_caption,
            parse_mode=constants.ParseMode.MARKDOWN
        )
        
        # 3. Instruction
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="🗣 Graba una nota de voz diciendo: **Annyeonghaseyo**"
        )
        # Cleanup
        audio_service.cleanup_files(tts_path)
        
    except Exception as e:
        logger.error(f"Error sending first lesson: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Error generando audio de lección.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main pipeline: Audio In -> Gemini Analysis -> Audio/Text Out."""
    user = update.message.from_user
    chat_id = update.effective_chat.id
    
    # Update User Profile in DB
    db_service.update_user(user.id, user.username, user.first_name)
    
    logger.info(f"Received voice note from {user.first_name} (ID: {user.id})")
    
    # Files to cleanup
    temp_files = []
    gemini_file = None

    try:
        # 1. Notify user "Recording/Typing" (UX)
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.RECORD_VOICE)

        # 2. Download Voice Note
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        ogg_path = f"voice_{user.id}_{update.message.message_id}.ogg"
        await voice_file.download_to_drive(ogg_path)
        temp_files.append(ogg_path)
        
        # 3. Convert to MP3
        mp3_path = audio_service.convert_ogg_to_mp3(ogg_path)
        temp_files.append(mp3_path)

        # 4. Upload to Gemini
        gemini_file = await gemini_service.upload_audio(mp3_path)

        # [DB] Retrieve Context (Deep Memory)
        previous_context = db_service.get_context(user.id, limit=50)
        logger.info(f"Retrieved {len(previous_context)} context items for user {user.id}")
        
        # 5. Get Analysis from Gemini
        # Keep "typing" status alive during AI processing
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        
        analysis = await gemini_service.analyze_audio(gemini_file, history=previous_context)
        
        # [DB] Save User Interaction
        db_service.save_interaction(
            user_id=user.id, 
            role='user', 
            audio_path=ogg_path, # Ideally we'd store file_id, but path is fine for logs
            analysis_data=analysis  # Save what the user SAID (transcription)
        )
        
        # 6. Generate TTS for the reply
        reply_text = analysis.get("reply_text", "Could not generate reply.")
        tts_filename = f"reply_{user.id}_{update.message.message_id}.mp3"
        tts_path = await audio_service.generate_tts(reply_text, output_file=tts_filename)
        temp_files.append(tts_path)

        # 7. Send Response - Audio Reply + Caption (Unified Bubble)
        # Construct Caption:
        # 🇰🇷 [Hangul]
        # 🔤 [Romanization]
        # 📖 [Phonetic-ES]
        # 🇪🇸 [Translation]
        caption_text = (
            f"🇰🇷 **{analysis.get('reply_text')}**\n"
            f"🔤 {analysis.get('reply_romanized', '')}\n"
            f"📖 *{analysis.get('reply_phonetic_es', 'No phonetic')}*\n"
            f"🇪🇸 {analysis.get('reply_translation', 'Trad: ???')}"
        )

        await context.bot.send_voice(
            chat_id=chat_id, 
            voice=open(tts_path, 'rb'),
            caption=caption_text,
            parse_mode=constants.ParseMode.MARKDOWN
        )

        # [DB] Save Model Reply
        db_service.save_interaction(
            user_id=user.id,
            role='model',
            content_text=reply_text,
            analysis_data={
                "feedback": analysis.get("feedback")
            }
        )

        # 9. Send Response - Step C: Feedback Card
        score = analysis.get("pronunciation_score", "?")
        emoji_score = "🟢" if int(score) >= 9 else "🟡" if int(score) >= 7 else "🔴"
        
        feedback_msg = (
            f"📊 **Pronunciation Score:** {score}/10 {emoji_score}\n\n"
            f"🗣 **You said:** {analysis.get('transcription')}\n"
            f"_{analysis.get('transcription_romanized')}_\n\n"
            f"💡 **Doctor's Feedback:**\n"
            f"{analysis.get('feedback')}"
        )
        
        await context.bot.send_message(
            chat_id=chat_id, 
            text=feedback_msg, 
            parse_mode=constants.ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error in handle_voice: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id, 
            text="⚠️ An error occurred while processing your voice. Please try again or check if the file is too short."
        )
    finally:
        # Cleanup
        audio_service.cleanup_files(*temp_files)
        if gemini_file:
            gemini_service.cleanup_gemini_file(gemini_file)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pipeline for TEXT input (e.g. 'Necesito decir...')."""
    user = update.message.from_user
    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    # Update User Profile in DB
    db_service.update_user(user.id, user.username, user.first_name)
    logger.info(f"Received TEXT from {user.first_name}: {user_text}")
    
    # Files to cleanup
    temp_files = []

    try:
        # [DB] Retrieve Context (Deep Memory)
        previous_context = db_service.get_context(user.id, limit=50)
        
        # Keep "typing" status alive during AI processing
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        
        # CALL GEMINI TEXT ANALYSIS
        analysis = await gemini_service.analyze_text(user_text, history=previous_context)
        
        # [DB] Save User Interaction
        db_service.save_interaction(
            user_id=user.id, 
            role='user', 
            content_text=user_text, # Save input text
            analysis_data={"transcription": user_text} # For consistency
        )
        
        # Generate TTS for the reply
        reply_text = analysis.get("reply_text", "Could not generate reply.")
        tts_filename = f"reply_text_{user.id}_{update.message.message_id}.mp3"
        tts_path = await audio_service.generate_tts(reply_text, output_file=tts_filename)
        temp_files.append(tts_path)

        # Send Response - Audio Reply + Caption
        caption_text = (
            f"🇰🇷 **{analysis.get('reply_text')}**\n"
            f"🔤 {analysis.get('reply_romanized', '')}\n"
            f"📖 *{analysis.get('reply_phonetic_es', 'No phonetic')}*\n"
            f"🇪🇸 {analysis.get('reply_translation', 'Trad: ???')}"
        )

        await context.bot.send_voice(
            chat_id=chat_id, 
            voice=open(tts_path, 'rb'),
            caption=caption_text,
            parse_mode=constants.ParseMode.MARKDOWN
        )

        # [DB] Save Model Reply
        db_service.save_interaction(
            user_id=user.id,
            role='model',
            content_text=reply_text,
            analysis_data={"feedback": analysis.get("feedback")}
        )

        # Feedback Card (Simplified for Text)
        feedback_msg = (
            f"💡 **Tip:**\n"
            f"{analysis.get('feedback')}"
        )
        
        await context.bot.send_message(
            chat_id=chat_id, 
            text=feedback_msg, 
            parse_mode=constants.ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error in handle_text: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Error processing text.")
    finally:
        audio_service.cleanup_files(*temp_files)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.VOICE, handle_voice)
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
    
    application.add_handler(start_handler)
    application.add_handler(voice_handler)
    application.add_handler(text_handler)
    
    logger.info("🤖 K-Voice Coach Bot is polling...")

    # Start the "Keep Alive" web server (for Render Free Tier)
    keep_alive()
    
    application.run_polling()
