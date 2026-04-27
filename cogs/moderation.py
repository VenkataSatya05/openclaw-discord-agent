"""
cogs/moderation.py — Server moderation tools.

Features:
    - Automatic bad-word filter (deletes message, issues warning)
    - Manual warn / mute / purge commands
    - Per-guild warning counters (in-memory)
"""

import asyncio
import re

import discord

from config import BAD_WORDS, MAX_WARNINGS

# In-memory warning store: { guild_id: { user_id: warning_count } }
_warnings: dict[int, dict[int, int]] = {}


# ── Helper ─────────────────────────────────────────────────────────────────────

def _find_bad_word(text: str) -> str | None:
    """Return the first matched bad word found in *text*, or ``None``."""
    lower = text.lower()
    for word in BAD_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", lower):
            return word
    return None


def _increment_warning(guild_id: int, user_id: int) -> int:
    """Increment and return the warning count for *user_id* in *guild_id*."""
    guild_data = _warnings.setdefault(guild_id, {})
    guild_data[user_id] = guild_data.get(user_id, 0) + 1
    return guild_data[user_id]


def find_member(guild: discord.Guild, name: str) -> discord.Member | None:
    """
    Look up a guild member by display name, username, or ID.

    Tries exact match first, then a case-insensitive substring match.
    """
    name_lower = name.lower().strip()
    for member in guild.members:
        if (
            member.display_name.lower() == name_lower
            or member.name.lower() == name_lower
            or str(member.id) == name_lower
        ):
            return member
    # Fuzzy fallback
    for member in guild.members:
        if name_lower in member.display_name.lower() or name_lower in member.name.lower():
            return member
    return None


# ── Auto bad-word filter ───────────────────────────────────────────────────────

async def bad_word_filter(message: discord.Message) -> bool:
    """
    Inspect *message* for profanity.

    If a bad word is detected:
        1. Delete the message.
        2. Increment the author's warning counter.
        3. Send a public warning (auto-deleted after 10 s).

    Returns ``True`` if the message was removed, ``False`` otherwise.
    """
    matched = _find_bad_word(message.content)
    if not matched:
        return False

    # Delete offending message
    try:
        await message.delete()
    except discord.Forbidden:
        pass  # Bot lacks Manage Messages — still warn

    guild_id = message.guild.id if message.guild else 0
    count    = _increment_warning(guild_id, message.author.id)

    warning = (
        f"⚠️ {message.author.mention} Watch your language! "
        f"That message was removed. **Warning {count}/{MAX_WARNINGS}**"
    )
    if count >= MAX_WARNINGS:
        warning += "\n🚨 You've hit the warning limit! Further violations may result in a mute."

    await message.channel.send(warning, delete_after=10)
    return True


# ── Manual moderation commands ─────────────────────────────────────────────────

async def warn_user(
    guild: discord.Guild,
    target: discord.Member,
    reason: str,
) -> str:
    """
    Issue a formal warning to *target*, DM them, and return a status string.
    """
    count = _increment_warning(guild.id, target.id)

    # Attempt to DM the warned user
    try:
        await target.send(
            f"⚠️ **Warning from {guild.name}**\n"
            f"Reason: {reason}\n"
            f"Warning count: {count}/{MAX_WARNINGS}"
        )
    except discord.Forbidden:
        pass  # DMs closed — warning still recorded

    return (
        f"⚠️ **{target.display_name}** has been warned.\n"
        f"📋 Reason: {reason}\n"
        f"🔢 Total warnings: **{count}/{MAX_WARNINGS}**"
    )


async def mute_user(
    guild: discord.Guild,
    target: discord.Member,
    duration_minutes: int,
    reason: str,
    channel: discord.TextChannel,
) -> str:
    """
    Mute *target* by assigning the ``Muted`` role for *duration_minutes* minutes.

    Creates the role and applies channel overwrites if it doesn't exist.
    Schedules an automatic unmute via asyncio.
    """
    try:
        mute_role = discord.utils.get(guild.roles, name="Muted")
        if not mute_role:
            mute_role = await guild.create_role(name="Muted", reason="Auto-created by bot")
            for ch in guild.channels:
                try:
                    await ch.set_permissions(mute_role, send_messages=False, speak=False)
                except discord.Forbidden:
                    pass

        await target.add_roles(mute_role, reason=reason)

        async def _unmute():
            await asyncio.sleep(duration_minutes * 60)
            try:
                await target.remove_roles(mute_role)
                await channel.send(f"🔊 **{target.display_name}** has been unmuted.")
            except Exception:
                pass

        asyncio.create_task(_unmute())

        return (
            f"🔇 **{target.display_name}** muted for **{duration_minutes} minute(s)**.\n"
            f"📋 Reason: {reason}"
        )

    except discord.Forbidden:
        return (
            "❌ I don't have permission to mute members.\n"
            "Make sure I have the **Manage Roles** permission and my role is above the target's."
        )
    except Exception as e:
        return f"❌ Mute error: {e}"


async def purge_messages(channel: discord.TextChannel, amount: int) -> str:
    """
    Bulk-delete up to *amount* messages (capped at 100) from *channel*.

    Returns a status string with the actual count deleted.
    """
    try:
        amount  = min(max(amount, 1), 100)
        deleted = await channel.purge(limit=amount)
        return f"🗑️ **Deleted {len(deleted)} message(s).**"
    except discord.Forbidden:
        return "❌ I don't have **Manage Messages** permission."
    except Exception as e:
        return f"❌ Purge error: {e}"