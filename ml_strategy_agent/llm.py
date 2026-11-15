"""
llm.py
------
LLM integration layer for the ML Strategy Agent.

Backend: Google Gemini (via google-genai SDK).
  - Primary model: gemini-2.0-flash-exp
  - Fallback model: gemini-1.5-flash-8b
  - Falls back to rule-based-only mode if no API key is found.

API key is loaded from GOOGLE_API_KEY in the environment (.env file).
"""

from __future__ import annotations
import os
import warnings
from dotenv import load_dotenv

load_dotenv()

# Filter harmless AFC UserWarning from google-genai SDK
warnings.filterwarnings("ignore", category=UserWarning, module="google.genai")

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


_PRIMARY_MODEL  = "gemini-2.0-flash"
_FALLBACK_MODEL = "gemini-1.5-flash-8b"

_GENERATION_CONFIG = {
    "temperature":      0.4,
    "top_p":            0.95,
    "max_output_tokens": 1024,
}


class GeminiLLM:
    """
    Wrapper around the Google Gemini API.

    Usage:
        llm = GeminiLLM()
        if llm.ready:
            text = llm.generate("Tell me about Random Forest.")
    """

    def __init__(self):
        self.ready:       bool = False
        self.model_name:  str  = ""
        self._client            = None

        if not _GENAI_AVAILABLE:
            print("[GeminiLLM] google-genai package not installed. LLM disabled.")
            return

        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            print("[GeminiLLM] No GOOGLE_API_KEY found in environment. LLM disabled.")
            return

        try:
            self._client = genai.Client(api_key=api_key)
            # Try primary model
            for model in (_PRIMARY_MODEL, _FALLBACK_MODEL):
                try:
                    test = self._client.models.generate_content(
                        model   = model,
                        contents= "Reply with exactly: READY",
                        config  = types.GenerateContentConfig(
                            temperature       = 0.0,
                            max_output_tokens = 10,
                        ),
                    )
                    if test and test.text:
                        self.model_name = model
                        self.ready      = True
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"[GeminiLLM] Failed to initialise Gemini client: {e}")

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the text response.

        Raises:
            RuntimeError if LLM is not ready.
        """
        if not self.ready:
            raise RuntimeError("GeminiLLM is not ready.")

        response = self._client.models.generate_content(
            model   = self.model_name,
            contents= prompt,
            config  = types.GenerateContentConfig(**_GENERATION_CONFIG),
        )
        return (response.text or "").strip()
