"""
app/config.py

Centralized configuration. Gemini is optional until later features need an LLM.
Feature 1 (Tavily) does not require GOOGLE_API_KEY.
"""

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def get_llm(temperature: float = 0.7):
    """
    Returns a Gemini LLM. Raises if GOOGLE_API_KEY is missing.
    Used by later features (rate / plan / write), not Feature 1.
    """
    if not GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. Add it to your .env file.\n"
            "Get a free key at: https://aistudio.google.com"
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )
