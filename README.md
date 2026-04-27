# 🍝 GitGud

The hyper-toxic Senior Developer bot that roasts your code using Groq-powered AI (LLaMA 3.3 70B).

## 🚀 Quick Start

1. **Clone the repository** (or just use these files).
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   - Copy `.env.example` to `.env`.
   - Add your `TELEGRAM_BOT_TOKEN` (from @BotFather).
   - Add your `GROQ_API_KEY` (from Groq Cloud).
   - (Optional, recommended) Add `GITHUB_TOKEN` to avoid GitHub API rate limits for repo-link reviews.
4. **Run the Bot**:
   ```bash
   python bot.py
   ```

## 🔥 Features

*   **Instant Roast**: Send any code snippet, get a savage critique.
*   **Repo Link Review**: Send a GitHub repository link and GitGud will sample files and roast the codebase automatically.
*   **Manager Mode**: Use `/manager_on` to have the bot check in on you every 2 hours. If you haven't submitted code, prepare for a sarcastic nudge.
*   **Smell Rating**: Every roast starts with a tier (Decent to Biological Hazard).
*   **The Least You Could Do**: A tiny, condescending tip at the end of every roast.

## 🛠️ Tech Stack

*   **Language**: Python 3.12+
*   **Library**: `python-telegram-bot` (Async)
*   **AI**: Groq Cloud API (LLaMA 3.3 70B Versatile)
*   **Database**: SQLite (via `aiosqlite`)
*   **Scheduling**: Built-in Telegram `JobQueue`

## ⚠️ Safety
Roasts are limited to coding skills. No hate speech or personal attacks outside the scope of developer incompetence.
