"""
cogs/leveling.py — Per-guild XP and level-up system.

XP is stored in memory (resets on bot restart).
For persistence across restarts, swap ``_xp_store`` with a JSON/SQLite backend.
"""

import discord
from config import XP_PER_MESSAGE, LEVEL_THRESHOLD

# In-memory store: { guild_id: { user_id: xp } }
_xp_store: dict[int, dict[int, int]] = {}


# ── Core XP logic ──────────────────────────────────────────────────────────────

def add_xp(guild_id: int, user_id: int) -> tuple[int, int, bool]:
    """
    Award ``XP_PER_MESSAGE`` XP to *user_id* in *guild_id*.

    Returns:
        (new_total_xp, current_level, leveled_up)
    """
    guild_data = _xp_store.setdefault(guild_id, {})
    guild_data[user_id] = guild_data.get(user_id, 0) + XP_PER_MESSAGE
    xp    = guild_data[user_id]
    level = xp // LEVEL_THRESHOLD

    # True when the XP crossed a level boundary this message
    leveled_up = (
        xp >= LEVEL_THRESHOLD
        and (xp % LEVEL_THRESHOLD) < XP_PER_MESSAGE
    )
    return xp, level, leveled_up


# ── Display helpers ────────────────────────────────────────────────────────────

def show_level(guild_id: int, user_id: int, display_name: str) -> str:
    """Return a formatted XP / level card for *display_name*."""
    xp           = _xp_store.get(guild_id, {}).get(user_id, 0)
    level        = xp // LEVEL_THRESHOLD
    progress     = xp % LEVEL_THRESHOLD
    next_xp      = (level + 1) * LEVEL_THRESHOLD
    filled       = int((progress / LEVEL_THRESHOLD) * 10)
    bar          = "█" * filled + "░" * (10 - filled)

    return (
        f"⭐ **{display_name}'s Stats**\n"
        f"🏅 Level: **{level}**\n"
        f"✨ XP: **{xp}** / {next_xp}\n"
        f"📊 Progress: `[{bar}]` {progress}/{LEVEL_THRESHOLD}"
    )


def show_leaderboard(guild_id: int, guild: discord.Guild) -> str:
    """Return a formatted top-10 XP leaderboard for *guild*."""
    data = _xp_store.get(guild_id, {})
    if not data:
        return "📭 No XP data yet — start chatting to earn XP!"

    top     = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    medals  = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines   = ["🏆 **Server Leaderboard**\n"]

    for i, (uid, xp) in enumerate(top):
        member = guild.get_member(uid)
        name   = member.display_name if member else f"User {uid}"
        level  = xp // LEVEL_THRESHOLD
        lines.append(f"{medals[i]} **{name}** — Level {level} ({xp} XP)")

    return "\n".join(lines)