import os
import random
from dotenv import load_dotenv

load_dotenv()

def get_groq_api_key():
    """
    Returns a random Groq API key from the available pool in .env
    to distribute Token Per Minute (TPM) load and avoid 429 errors.
    """
    keys = [
        (os.getenv("GROQ_API_KEY") or "").strip().strip('"').strip("'"),
        (os.getenv("GROQ_API_KEY_2") or "").strip().strip('"').strip("'"),
        (os.getenv("GROQ_API_KEY_3") or "").strip().strip('"').strip("'")
    ]
    # Filter out None/Empty keys and placeholders
    valid_keys = [k for k in keys if k and len(k) > 20 and "from screenshot" not in k]
    
    if not valid_keys:
        # Fallback to the first key if everything fails, but try to be safe
        first_key = os.getenv("GROQ_API_KEY")
        if first_key: return first_key
        raise ValueError("No valid GROQ_API_KEY found in .env")
        
    return random.choice(valid_keys)
