"""
main.py — Discord bot entry point.

Registers all Discord events and prefix commands, then runs the bot.
All heavy logic lives in agent.py and the cogs/ modules.

Run:
    python main.py
"""

import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN, COMMAND_PREFIX, BOT_NAME, MAX_HISTORY,
)
from agent import run_agent
from cogs.info       import scheduler
from cogs.leveling   import add_xp, show_level, show_leaderboard
from cogs.moderation import bad_word_filter, warn_user, mute_user, purge_messages, find_member
from cogs.music      import play, pause, resume, skip, stop, get_queue, music_queues
from cogs.fun        import tell_joke, magic_8ball, roast, get_meme, start_game

# ── Bot setup ──────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.guilds          = True
intents.voice_states    = True
intents.members         = True   # required for moderation member lookups

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Per-channel conversation history: { channel_id: [ {role, content}, ... ] }
_conversation_history: dict[str, list[dict]] = {}


# ── Events ─────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    scheduler.start()
    print(f"✅ {BOT_NAME} is online as {bot.user}")
    print(f"   Model    : from config.py → OLLAMA_MODEL")
    print(f"   Search   : Wikipedia → Bing (no key needed)")
    print(f"   Music    : yt-dlp + FFmpeg")
    print(f"   Games    : RPS · Number Guess · Trivia · Truth or Dare")
    print(f"   Mod      : Bad-word filter · Warn · Mute · Purge")
    print(f"   Leveling : XP per message · Leaderboard")
    print(f"   Scheduler: APScheduler running")
    print("─" * 50)


@bot.event
async def on_message(message: discord.Message):
    # Never process our own messages
    if message.author == bot.user:
        return

    # Let prefix commands through first
    await bot.process_commands(message)

    # ── Automatic bad-word filter (all non-bot guild messages) ────────────────
    if message.guild and not message.author.bot:
        deleted = await bad_word_filter(message)
        if deleted:
            return   # don't process a deleted message further

    # ── XP for every guild message ────────────────────────────────────────────
    if message.guild and not message.author.bot:
        xp, level, leveled_up = add_xp(message.guild.id, message.author.id)
        if leveled_up:
            await message.channel.send(
                f"🎉 {message.author.mention} leveled up to **Level {level}**! ⭐",
                delete_after=15,
            )

    # ── Only respond when @mentioned ──────────────────────────────────────────
    if bot.user not in message.mentions:
        return

    user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()

    # Empty mention → show help
    if not user_input:
        await message.reply(
            f"Hey! I'm **{BOT_NAME}** 👋\n\n"
            f"**What I can do:**\n"
            f"🌤 Weather · 🔍 Search · 🎵 Music · ⏰ Reminders · 🧮 Math\n"
            f"😂 Jokes · 🎱 Magic 8-Ball · 🔥 Roast · 🎮 Games · 🏆 Levels\n"
            f"🛡️ Warn / Mute / Purge *(mods only)*\n\n"
            f"Try: `@{BOT_NAME} tell me a dad joke` or `@{BOT_NAME} play trivia`"
        )
        return

    print(f"\n📨 [{message.guild}] {message.author}: {user_input}")

    async with message.channel.typing():
        channel_id = str(message.channel.id)
        history    = _conversation_history.setdefault(channel_id, [])

        try:
            reply = await run_agent(user_input, history, message, bot)
        except Exception as e:
            reply = f"⚠️ An unexpected error occurred: {e}"
            print(f"  ❌ {e}")

        # Trim history to avoid unbounded growth
        if len(history) > MAX_HISTORY * 2:
            _conversation_history[channel_id] = history[-(MAX_HISTORY * 2):]

        if not reply:
            return   # tool already sent its own message

        # Split long replies into 1900-char chunks (Discord limit = 2000)
        if len(reply) > 1900:
            for chunk in [reply[i:i + 1900] for i in range(0, len(reply), 1900)]:
                await message.reply(chunk)
        else:
            await message.reply(reply)


# ── Prefix commands — Music ────────────────────────────────────────────────────

@bot.command(name="play")
async def cmd_play(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("❌ Join a voice channel first!")
        return
    await play(ctx.guild.id, ctx.author.voice.channel, ctx.channel, query, bot)

@bot.command(name="pause")
async def cmd_pause(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    await ctx.send(pause(vc))

@bot.command(name="resume")
async def cmd_resume(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    await ctx.send(resume(vc))

@bot.command(name="skip")
async def cmd_skip(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    await ctx.send(skip(vc))

@bot.command(name="stop")
async def cmd_stop(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    await ctx.send(await stop(vc, ctx.guild.id))

@bot.command(name="queue")
async def cmd_queue(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    await ctx.send(get_queue(ctx.guild.id, vc))


# ── Prefix commands — Moderation ──────────────────────────────────────────────

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def cmd_warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await ctx.send(await warn_user(ctx.guild, member, reason))

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def cmd_mute(ctx, member: discord.Member, duration: int = 10, *, reason: str = "No reason"):
    await ctx.send(await mute_user(ctx.guild, member, duration, reason, ctx.channel))

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def cmd_purge(ctx, amount: int = 10):
    await ctx.message.delete()
    result = await purge_messages(ctx.channel, amount)
    await ctx.send(result, delete_after=5)


# ── Prefix commands — Leveling ────────────────────────────────────────────────

@bot.command(name="level")
async def cmd_level(ctx):
    await ctx.send(show_level(ctx.guild.id, ctx.author.id, ctx.author.display_name))

@bot.command(name="leaderboard")
async def cmd_leaderboard(ctx):
    await ctx.send(show_leaderboard(ctx.guild.id, ctx.guild))


# ── Prefix commands — Fun ─────────────────────────────────────────────────────

@bot.command(name="joke")
async def cmd_joke(ctx, joke_type: str = "random"):
    await ctx.send(tell_joke(joke_type))

@bot.command(name="8ball")
async def cmd_8ball(ctx, *, question: str = ""):
    await ctx.send(magic_8ball(question))

@bot.command(name="roast")
async def cmd_roast(ctx, member: discord.Member = None):
    target = member.display_name if member else ctx.author.display_name
    await ctx.send(roast(target))

@bot.command(name="meme")
async def cmd_meme(ctx):
    await ctx.send(get_meme())

@bot.command(name="game")
async def cmd_game(ctx, *, game_type: str = "random"):
    await ctx.send(start_game(game_type, str(ctx.channel.id), str(ctx.author.id)))


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set. Add it to your .env file.")
    print(f"🚀 Starting {BOT_NAME}…")
    print("─" * 50)
    bot.run(DISCORD_TOKEN)