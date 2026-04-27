import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

import database as db
import ai_engine as ai

load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NUDGE_THRESHOLD = int(os.getenv("NUDGE_THRESHOLD", 7200)) # 2 hours
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 1800)) # 30 mins

CODE_KEYWORDS = [
    r'\{', r'\}', r';', r'def ', r'function ', r'const ', r'let ', r'var ',
    r'import ', r'from ', r'#include', r'public class', r'async ', r'await ',
    r'print\(', r'console\.log', r'=', r'\+', r'-', r'\*', r'/'
]

def is_code(text):
    if not text or len(text) < 5:
        return False
    # Simple heuristic: check for common code markers
    matches = sum(1 for pattern in CODE_KEYWORDS if re.search(pattern, text))
    # If it has multiple lines or common code symbols, it's probably code
    return matches >= 1 or '\n' in text or (text.strip().startswith('```') and text.strip().endswith('```'))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.update_last_submission(user.id, user.username)
    
    welcome_text = (
        "🍝 *GitGud v1.2*\n\n"
        "I am the Senior Architect you never wanted. Throw your code at me, "
        "and I'll tell you exactly why you're an overhead cost.\n\n"
        "Commands:\n"
        "/roast <your code> - Force a roast even if I don't think it's code\n"
        "/manager_on - Enable Manager Mode (I'll pester you if you're lazy)\n"
        "/manager_off - Disable Manager Mode\n"
        "/status - Check your current 'Smell' standing"
    )
    await update.message.reply_text(welcome_text, parse_mode=constants.ParseMode.MARKDOWN)

async def manager_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.toggle_manager_mode(update.effective_user.id, True)
    await update.message.reply_text("🚩 *Manager Mode: ON*\n\nIf I don't see code every 2 hours, expect a visit.", parse_mode=constants.ParseMode.MARKDOWN)

async def manager_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.toggle_manager_mode(update.effective_user.id, False)
    await update.message.reply_text("🤡 *Manager Mode: OFF*\n\nBack to slacking, I see.", parse_mode=constants.ParseMode.MARKDOWN)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = await db.get_user(update.effective_user.id)
    if not user_data:
        await update.message.reply_text("You haven't even started working. Type /start.")
        return
    
    manager = "ON" if user_data[2] else "OFF"
    await update.message.reply_text(f"📊 *Status Report*\nManager Mode: {manager}\n\nKeep working or get fired.", parse_mode=constants.ParseMode.MARKDOWN)

async def perform_roast(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    if len(code) > 10000:
        await update.message.reply_text("🛑 This wall of text is longer than your career. Keep it under 10,000 chars.")
        return

    # Build anticipation
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Update last submission time
    await db.update_last_submission(update.effective_user.id, update.effective_user.username)
    
    # Get Roast
    roast = await ai.get_roast(code)
    
    # Share button
    keyboard = [[InlineKeyboardButton("🔥 Share Roast", switch_inline_query=roast[:50])]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(roast, reply_markup=reply_markup)

async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = " ".join(context.args)
    if not code:
        await update.message.reply_text("Usage: /roast <your pathetic code>")
        return
    await perform_roast(update, context, code)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    
    logger.info(f"Received message from {update.effective_user.username}: {text[:20]}...")

    if is_code(text):
        await perform_roast(update, context, text)
    else:
        # Check if bot is mentioned or it's a private chat
        is_private = update.effective_chat.type == constants.ChatType.PRIVATE
        is_mentioned = context.bot.username and f"@{context.bot.username}" in text
        
        if is_private or is_mentioned:
             await update.message.reply_text("That's not code. Send code or get back to Jira.")

async def nudge_job(context: ContextTypes.DEFAULT_TYPE):
    users_to_nudge = await db.get_users_for_nudge(NUDGE_THRESHOLD)
    for (user_id,) in users_to_nudge:
        try:
            nudge_msg = await ai.get_nudge()
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ *MANAGER NUDGE*\n\n{nudge_msg}", parse_mode=constants.ParseMode.MARKDOWN)
            await db.mark_nudged(user_id)
        except Exception as e:
            logger.error(f"Failed to nudge {user_id}: {e}")

async def post_init(application):
    await db.init_db()
    logger.info("Database initialized.")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            # Bot itself joined
            await update.message.reply_text(
                "🍝 *GitGud has entered the chat.*\n\n"
                "I'm here to watch your production crashes and laugh. "
                "Type /start to see how I can ruin your day.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        else:
            # Someone else joined
            welcome_msgs = [
                f"Oh look, another 'Developer' joined: @{new_member.username or new_member.first_name}. I hope your code is better than your profile picture.",
                f"Welcome @{new_member.username or new_member.first_name}. Please don't push to main while I'm looking.",
                f"Fresh meat! @{new_member.username or new_member.first_name}, I've already smelled your code from the invite link. It's a biohazard."
            ]
            import random
            await update.message.reply_text(random.choice(welcome_msgs))

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('manager_on', manager_on))
    application.add_handler(CommandHandler('manager_off', manager_off))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('roast', roast_command))
    
    # Welcome message for new members
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Scheduler
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(nudge_job, interval=CHECK_INTERVAL, first=10)
    else:
        logger.warning("JobQueue not available. Manager nudges will not work.")
    
    logger.info("🍝 GitGud is hunting for code...")
    application.run_polling()
