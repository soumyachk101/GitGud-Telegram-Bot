import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

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
