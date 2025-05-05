import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_OWNER_ID = 1918624551
group_settings = {}
music_library = {}

def get_group_id(update: Update):
    return update.effective_chat.id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Squonk Radio V0.4.3!\nUse /setup to link your group.")

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("⚠️ Please use this command in private chat.")
    if update.effective_user.id != BOT_OWNER_ID:
        return await update.message.reply_text("❌ Only the owner can setup groups.")
    if not context.args:
        return await update.message.reply_text("📥 Send me `GroupID: <your_group_id>` to register a group.")
    group_id = context.args[0]
    group_settings[group_id] = {"songs": []}
    await update.message.reply_text(f"✅ Group ID `{group_id}` saved. Now send me .mp3 files!")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        return await update.message.reply_text("❌ Only the bot owner can upload songs.")
    audio = update.message.audio or update.message.voice or update.message.document
    if not audio or not audio.file_name.endswith(".mp3"):
        return await update.message.reply_text("⚠️ Only .mp3 files are supported.")
    file = await context.bot.get_file(audio.file_id)
    path = f"{audio.file_unique_id}.mp3"
    await file.download_to_drive(path)
    tags = ID3(path)
    title = tags.get("TIT2", TIT2(encoding=3, text="Unknown")).text[0]
    artist = tags.get("TPE1", TPE1(encoding=3, text="Unknown")).text[0]
    song_info = {"title": title, "artist": artist, "file_id": audio.file_id}
    for group_id in group_settings:
        group_settings[group_id]["songs"].append(song_info)
    os.remove(path)
    await update.message.reply_text(f"✅ Saved `{title}` by `{artist}`.")

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = str(update.effective_chat.id)
    songs = group_settings.get(group_id, {}).get("songs", [])
    if not songs:
        return await update.message.reply_text("❌ No songs found for this group.")
    current = songs[0]
    await context.bot.send_audio(chat_id=group_id, audio=current["file_id"],
                                 caption="🎵 Squonking time!",
                                 reply_markup=InlineKeyboardMarkup([[
                                     InlineKeyboardButton("▶ Playlist", callback_data="playlist"),
                                     InlineKeyboardButton("⏭ Next", callback_data="next")
                                 ]]))

async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    group_id = str(query.message.chat.id)
    songs = group_settings.get(group_id, {}).get("songs", [])
    if not songs:
        await query.answer("No songs found.")
        return
    text = "🎵 Playlist:\n" + "\n".join(f"{i+1}. {s['title']}" for i, s in enumerate(songs))
    await query.edit_message_text(text)

async def next_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    group_id = str(query.message.chat.id)
    songs = group_settings.get(group_id, {}).get("songs", [])
    if not songs:
        return await query.answer("❌ No songs to play.")
    current = songs.pop(0)
    songs.append(current)
    await context.bot.send_audio(chat_id=group_id, audio=songs[0]["file_id"],
                                 caption="🎶 Next up!",
                                 reply_markup=InlineKeyboardMarkup([[
                                     InlineKeyboardButton("▶ Playlist", callback_data="playlist"),
                                     InlineKeyboardButton("⏭ Next", callback_data="next")
                                 ]]))
    await query.answer()

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(MessageHandler(filters.Document.MP3, handle_audio))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(playlist, pattern="^playlist$"))
    app.add_handler(CallbackQueryHandler(next_song, pattern="^next$"))
    app.run_polling()

if __name__ == "__main__":
    main()
