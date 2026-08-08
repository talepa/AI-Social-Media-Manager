"""
app/config.py

Centralized configuration loader.

WHY a central config?
- All agents import the LLM from ONE place. If we switch models later,
  we change it here and every agent picks it up automatically.
- python-dotenv loads the .env file so environment variables are available
  both when running locally and inside Docker.
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load .env from the project root (two levels up from this file)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "GOOGLE_API_KEY is not set. Add it to your .env file.\n"
        "Get a free key at: https://aistudio.google.com"
    )


def get_llm(temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    """
    Returns a configured Gemini LLM instance.

    WHY a factory function?
    - Agents may need different temperatures (e.g. writer needs more creativity
      than the planner which needs more consistency).
    - Centralising construction means we can add retries, fallbacks, or
      model switching in one place without touching agent code.

    Args:
        temperature: Controls creativity. 0.0 = deterministic, 1.0 = very creative.
    """
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )
