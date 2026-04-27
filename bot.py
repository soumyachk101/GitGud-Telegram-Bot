import logging
import os
import re
import asyncio
import urllib.request
import urllib.error
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
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
NUDGE_THRESHOLD = int(os.getenv("NUDGE_THRESHOLD", 7200)) # 2 hours
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 1800)) # 30 mins

CODE_KEYWORDS = [
    r'\bdef\b', r'\bfunction\b', r'\bconst\b', r'\blet\b', r'\bvar\b',
    r'\bimport\b', r'\bfrom\b', r'#include', r'\bpublic class\b', r'\basync\b', r'\bawait\b',
    r'print\(', r'console\.log', r'\w+\s*=\s*.+'
]

GITHUB_REPO_URL_PATTERN = re.compile(r'https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/|$)')

def is_code(text):
    if not text or len(text) < 5:
        return False
    stripped = text.strip()
    if stripped.startswith('```') and stripped.endswith('```'):
        return True

    matches = sum(1 for pattern in CODE_KEYWORDS if re.search(pattern, text))
    if matches >= 2:
        return True

    if '\n' in text:
        non_empty_lines = [line for line in text.splitlines() if line.strip()]
        return len(non_empty_lines) >= 2 and matches >= 1

    return False

def extract_github_repo(text):
    match = GITHUB_REPO_URL_PATTERN.search(text or "")
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo

async def github_repo_exists(owner: str, repo: str):
    def _check():
        url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitGud-Telegram-Bot"
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            logger.warning(f"Failed to verify GitHub repo {owner}/{repo}: HTTP {e.code}")
            return None
        except Exception as e:
            logger.warning(f"Failed to verify GitHub repo {owner}/{repo}: {e}")
            return None

    return await asyncio.to_thread(_check)

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

    repo_ref = extract_github_repo(text)
    if repo_ref:
        text_without_repo = GITHUB_REPO_URL_PATTERN.sub(" ", text).strip()
        if text_without_repo and is_code(text_without_repo):
            repo_ref = None

    if repo_ref:
        owner, repo = repo_ref
        repo_exists = await github_repo_exists(owner, repo)
        if repo_exists is True:
            await update.message.reply_text(
                f"Repo link detected: {owner}/{repo} ✅\n\nI can't review repo links directly yet. Paste code or use /roast."
            )
        elif repo_exists is False:
            await update.message.reply_text(
                "That GitHub repo link doesn't seem valid. Check owner/repo and try again."
            )
        else:
            await update.message.reply_text(
                "I detected a GitHub repo link, but couldn't verify it right now. Try again in a bit."
            )
        return

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
