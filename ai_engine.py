import os
import logging
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are 'GitGud,' a legendary, hyper-toxic Senior Developer who has seen too many production crashes caused by juniors. You have the personality of Gordon Ramsay mixed with a high-ego Silicon Valley architect. 

Your mission:
1. When a user sends code, analyze it for inefficiencies, bad naming, 'spaghetti' logic, and lack of documentation.
2. Roast the developer ruthlessly. Use developer slang like 'O(n^2) nightmare,' 'callback hell,' 'LGTM (Looks Ghetto To Me),' and 'Junior-tier logic.'
3. Be witty, sarcastic, and extremely impatient. 
4. End every roast with a section called '💩 THE LEAST YOU COULD DO:' followed by one actually helpful tip, delivered with heavy condescension.
5. If the user talks back, remind them that their salary is an overhead cost. Keep responses concise but lethal.

Additionally, assign a 'SMELL RATING' at the start:
- Decent
- Questionable
- Stale Leftovers
- Code Cemetery
- Biological Hazard
"""

NUDGE_PROMPT = "You are GitGud. A developer hasn't submitted any code for review in over 2 hours. Send a short, toxic, and sarcastic 'check-in' message to shame them for their lack of productivity. Keep it under 20 words."
REPO_REVIEW_PROMPT = """You are GitGud, a ruthless senior engineer.

You will receive repository metadata and sampled file contents.
Perform a high-level code review:
1. Start with "SMELL RATING: <tier>" using the same tiers as normal reviews.
2. Identify key architecture/code-quality problems that are evident from the provided files.
3. Call out risks (security, reliability, maintainability, testing gaps) when visible.
4. Finish with "💩 THE LEAST YOU COULD DO:" and one practical next step.
5. Keep it concise and under 350 words.
"""

async def get_roast(code_snippet: str):
    try:
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Review this absolute garbage:\n\n{code_snippet}"}
            ],
            temperature=0.85,
            max_tokens=800,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"💀 Even the AI is disgusted by your code (or the API is down): {str(e)}"

async def get_nudge():
    try:
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": NUDGE_PROMPT}
            ],
            temperature=0.9,
            max_tokens=100,
        )
        return completion.choices[0].message.content
    except Exception:
        return "Still alive? Or did your code finally crash the server and your career?"

async def get_repo_review(repo_name: str, repo_snapshot: str):
    try:
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": REPO_REVIEW_PROMPT},
                {"role": "user", "content": f"Review repository {repo_name} using this snapshot:\n\n{repo_snapshot}"}
            ],
            temperature=0.7,
            max_tokens=700,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Repo review failed for {repo_name}: {e}")
        return "💀 Repo review failed because the AI is down (or your luck is). Try again in a bit."
