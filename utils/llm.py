"""
utils/llm.py — Thin wrapper around the Ollama /api/chat endpoint.

Usage:
    from utils.llm import chat_with_ollama

    reply = chat_with_ollama(messages=[...], temperature=0.7)
"""

# import requests
# from config import OLLAMA_URL, OLLAMA_MODEL


# def chat_with_ollama(messages: list[dict], temperature: float = 0.2) -> str:
#     """
#     Send a list of chat messages to the local Ollama model and return the reply.

#     Args:
#         messages:    List of {"role": ..., "content": ...} dicts.
#         temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).

#     Returns:
#         The model's reply as a plain string, or an error message.
#     """
#     try:
#         res = requests.post(
#             OLLAMA_URL,
#             json={
#                 "model":    OLLAMA_MODEL,
#                 "messages": messages,
#                 "stream":   False,
#                 "options":  {"temperature": temperature},
#             },
#             timeout=120,
#         )
#         res.raise_for_status()
#         return res.json()["message"]["content"].strip()

#     except requests.exceptions.ConnectionError:
#         return "ERROR: Cannot connect to Ollama. Make sure `ollama serve` is running."
#     except Exception as e:
#         return f"ERROR: {e}"

import asyncio
import requests
from config import OLLAMA_URL, OLLAMA_MODEL

def _call_ollama(messages: list[dict], temperature: float) -> str:
    """Synchronous Ollama call — run this in an executor, never directly."""
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model":    OLLAMA_MODEL,
                "messages": messages,
                "stream":   False,
                "options":  {"temperature": temperature},
            },
            timeout=120,
        )
        res.raise_for_status()
        return res.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Make sure `ollama serve` is running."
    except Exception as e:
        return f"ERROR: {e}"


async def chat_with_ollama(messages: list[dict], temperature: float = 0.2) -> str:
    """Async wrapper — runs the blocking HTTP call in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _call_ollama, messages, temperature
    )