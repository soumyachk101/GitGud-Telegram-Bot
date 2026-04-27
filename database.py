import aiosqlite
import time

DB_PATH = "spaghettisniffer.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                manager_mode INTEGER DEFAULT 0,
                last_submission_time REAL DEFAULT 0,
                last_nudge_time REAL DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_last_submission(user_id, username=None):
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, last_submission_time) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                last_submission_time = excluded.last_submission_time,
                username = COALESCE(excluded.username, users.username)
        """, (user_id, username, now))
        await db.commit()

async def toggle_manager_mode(user_id, status: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, manager_mode) 
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET manager_mode = excluded.manager_mode
        """, (user_id, 1 if status else 0))
        await db.commit()

async def get_users_for_nudge(threshold_seconds: int):
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        # Get users who have manager_mode ON and haven't submitted in threshold
        # And haven't been nudged in the last 2 hours (to avoid spamming)
        async with db.execute("""
            SELECT user_id FROM users 
            WHERE manager_mode = 1 
            AND last_submission_time < ? 
            AND last_nudge_time < ?
        """, (now - threshold_seconds, now - threshold_seconds)) as cursor:
            return await cursor.fetchall()

async def mark_nudged(user_id):
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_nudge_time = ? WHERE user_id = ?", (now, user_id))
        await db.commit()
