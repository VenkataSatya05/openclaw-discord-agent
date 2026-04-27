"""
config.py — Central configuration for the Discord AI Agent.
All tunable constants live here. Import from this file everywhere else.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Discord ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
BOT_NAME:      str = "Agent"
COMMAND_PREFIX: str = "!"

# ── Ollama ─────────────────────────────────────────────────────────────────────
OLLAMA_MODEL: str = "qwen2.5:3b"
OLLAMA_URL:   str = "http://localhost:11434/api/chat"

# ── APIs ───────────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

# ── Bot behaviour ──────────────────────────────────────────────────────────────
BOT_TIMEZONE:  str = "Asia/Kolkata"
MAX_HISTORY:   int = 10          # conversation turns kept per channel

# ── XP system ─────────────────────────────────────────────────────────────────
XP_PER_MESSAGE:  int = 10
LEVEL_THRESHOLD: int = 100       # XP needed per level

# ── Moderation ─────────────────────────────────────────────────────────────────
MAX_WARNINGS: int = 3            # warnings before escalation notice

BAD_WORDS: list[str] = [
    "fuck", "shit", "bitch", "asshole", "bastard", "damn", "crap",
    "piss", "dick", "cock", "pussy", "nigger", "nigga", "faggot",
    "retard", "whore", "slut", "cunt", "motherfucker", "bullshit",
]

# ── Music ──────────────────────────────────────────────────────────────────────
# Update this path if ffmpeg is not on your system PATH
FFMPEG_PATH: str = (
    r"C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
)

YTDL_OPTIONS: dict = {
    "format":         "bestaudio/best",
    "noplaylist":     True,
    "quiet":          True,
    "no_warnings":    True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS: dict = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options":        "-vn",
}