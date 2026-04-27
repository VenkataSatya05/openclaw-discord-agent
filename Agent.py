"""
agent.py — The central "brain" of the Discord AI Agent.

Receives every user message, decides which tool to invoke (via the LLM router),
executes the tool, and returns a final Discord-ready string.

Import ``run_agent`` from here and call it inside the on_message handler.
"""

import discord

from config import BOT_TIMEZONE, BOT_NAME
from utils.llm    import chat_with_ollama
from utils.router import ROUTER_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT, extract_json
from utils.search import search_web

import cogs.info        as info_cog
import cogs.music       as music_cog
import cogs.fun         as fun_cog
import cogs.leveling    as leveling_cog
import cogs.moderation  as mod_cog

# Keywords that trigger a search fallback even when the router says NO_TOOL
_SEARCH_KEYWORDS = [
    "score", "match", "ipl", "cricket", "football", "nba", "yesterday",
    "today", "latest", "recent", "news", "price", "stock", "winner",
    "result", "top", "best", "greatest", "richest", "list", "ranking",
    "history", "who is", "what is", "capital", "population",
    "world cup", "how many", "when did", "who won",
]


async def run_agent(
    user_message: str,
    history: list[dict],
    message: discord.Message,
    bot,
) -> str:
    """
    Process *user_message* and return the bot's reply.

    Steps:
        1. Check for an active mini-game and handle in-game input.
        2. Ask the router LLM which tool to call.
        3. Execute the chosen tool.
        4. Fall back to keyword-triggered search if the router chose NO_TOOL
           but the message looks like a factual query.
        5. Pass tool output (or nothing) to the chat LLM for a natural reply.

    Args:
        user_message: The cleaned text the user sent (mention stripped).
        history:      The mutable conversation history list for this channel.
        message:      The original discord.Message object.
        bot:          The discord.ext.commands.Bot instance.

    Returns:
        A string ready to be sent as a Discord message.
    """
    channel_id = str(message.channel.id)
    user_id    = str(message.author.id)
    guild_id   = message.guild.id if message.guild else None

    # ── 1. Active game input ─────────────────────────────────────────────────
    game_reply = fun_cog.process_game_input(user_message, channel_id, user_id)
    if game_reply:
        return game_reply

    # ── 2. Route ─────────────────────────────────────────────────────────────
    router_reply =await chat_with_ollama(
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.0,
    )
    print(f"  🔀 Router → {router_reply[:120]}")

    tool_result: str | None = None

    if "NO_TOOL" not in router_reply.upper():
        data = extract_json(router_reply)
        if data:
            tool_result = await _dispatch_tool(
                data, user_message, channel_id, user_id, guild_id, message, bot
            )
            # _dispatch_tool returns a sentinel for early-return tools
            if tool_result is _EARLY_RETURN:
                return ""   # message already sent by the tool

    # ── 3. Keyword search fallback ────────────────────────────────────────────
    if tool_result is None:
        if any(kw in user_message.lower() for kw in _SEARCH_KEYWORDS):
            tool_result = await search_web(user_message.strip())

    # ── 4. Build final reply ──────────────────────────────────────────────────
    history.append({"role": "user", "content": user_message})

    if tool_result:
        history.append({
            "role":    "user",
            "content": f"Tool data:\n\n{tool_result}\n\nRespond to the user based on this data.",
        })

    reply =await chat_with_ollama(
        messages=[{"role": "system", "content": CHAT_SYSTEM_PROMPT}] + history,
        temperature=0.7,
    )
    history.append({"role": "assistant", "content": reply})
    return reply


# ── Sentinel object for tools that send their own Discord messages ─────────────
_EARLY_RETURN = object()


async def _dispatch_tool(
    data: dict,
    user_message: str,
    channel_id: str,
    user_id: str,
    guild_id: int | None,
    message: discord.Message,
    bot,
) -> str | object | None:
    """
    Execute the tool specified in *data* and return its string result.

    Returns ``_EARLY_RETURN`` for tools that send messages themselves
    (e.g. music, which sends multiple messages asynchronously).
    Returns ``None`` if the tool could not be dispatched.
    """
    tool = data.get("tool")
    args = data.get("args", {})
    print(f"  🔧 Tool: {tool}({args})")

    # ────────────────────────────────── Music ─────────────────────────────────
    if tool == "play_music":
        if not guild_id:
            return "❌ Music only works inside a server."
        if not message.author.voice:
            return "❌ You need to **join a voice channel** first!"
        import asyncio
        asyncio.create_task(
            music_cog.play(
                guild_id,
                message.author.voice.channel,
                message.channel,
                args.get("query", user_message),
                bot,
            )
        )
        return _EARLY_RETURN

    if tool == "pause_music":
        vc = discord.utils.get(bot.voice_clients, guild=message.guild)
        return music_cog.pause(vc)

    if tool == "resume_music":
        vc = discord.utils.get(bot.voice_clients, guild=message.guild)
        return music_cog.resume(vc)

    if tool == "skip_music":
        vc = discord.utils.get(bot.voice_clients, guild=message.guild)
        return music_cog.skip(vc)

    if tool == "stop_music":
        vc = discord.utils.get(bot.voice_clients, guild=message.guild)
        return await music_cog.stop(vc, guild_id)

    if tool == "show_queue":
        vc = discord.utils.get(bot.voice_clients, guild=message.guild)
        return music_cog.get_queue(guild_id, vc)

    # ────────────────────────────────── Fun ───────────────────────────────────
    if tool == "tell_joke":
        return fun_cog.tell_joke(args.get("joke_type", "random"))

    if tool == "magic_8ball":
        return fun_cog.magic_8ball(args.get("question", ""))

    if tool == "roast":
        target = args.get("target", message.author.display_name)
        return fun_cog.roast(target)

    if tool == "meme":
        return fun_cog.get_meme()

    if tool == "play_game":
        return fun_cog.start_game(
            args.get("game_type", "random"), channel_id, user_id
        )

    # ────────────────────────────────── Leveling ──────────────────────────────
    if tool == "show_level":
        if "leaderboard" in user_message.lower() and message.guild:
            return leveling_cog.show_leaderboard(guild_id, message.guild)
        return leveling_cog.show_level(
            guild_id, message.author.id, message.author.display_name
        )

    # ────────────────────────────────── Moderation ────────────────────────────
    if tool == "warn_user" and message.guild:
        if not message.author.guild_permissions.manage_messages:
            return "❌ You need **Manage Messages** permission to warn users."
        target = mod_cog.find_member(message.guild, args.get("username", ""))
        if not target:
            return f"❌ Could not find member **{args.get('username')}**."
        return await mod_cog.warn_user(
            message.guild, target, args.get("reason", "No reason provided")
        )

    if tool == "mute_user" and message.guild:
        if not message.author.guild_permissions.manage_roles:
            return "❌ You need **Manage Roles** permission to mute users."
        target = mod_cog.find_member(message.guild, args.get("username", ""))
        if not target:
            return f"❌ Could not find member **{args.get('username')}**."
        return await mod_cog.mute_user(
            message.guild,
            target,
            int(args.get("duration_minutes", 10)),
            args.get("reason", "No reason provided"),
            message.channel,
        )

    if tool == "purge_messages" and message.guild:
        if not message.author.guild_permissions.manage_messages:
            return "❌ You need **Manage Messages** permission to purge."
        return await mod_cog.purge_messages(
            message.channel, int(args.get("amount", 10))
        )

    # ────────────────────────────────── Info / utilities ──────────────────────
    if tool == "get_weather":
        return info_cog.get_weather(**args)

    if tool == "get_time":
        return info_cog.get_time(**args)

    if tool == "calculate":
        return info_cog.calculate(**args)

    if tool == "schedule_message":
        args["channel_id"] = channel_id
        args["user_id"]    = user_id
        args["bot"]        = bot
        return info_cog.schedule_message(**args)

    if tool == "create_server":
        return await info_cog.create_discord_server(bot=bot, **args)

    if tool == "search_web":
        return await search_web(args.get("query", user_message))

    return None