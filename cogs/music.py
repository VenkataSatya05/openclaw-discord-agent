"""
cogs/music.py — YouTube music playback via yt-dlp + FFmpeg.

Manages per-guild voice connections and song queues.
All public functions are async and intended to be called from the agent brain
or from discord.py prefix-command handlers.
"""

import asyncio

import discord
import yt_dlp

from config import FFMPEG_PATH, FFMPEG_OPTIONS, YTDL_OPTIONS

# Shared yt-dlp instance (stateless — safe to reuse)
_ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# Per-guild song queues:  { guild_id: [ {"title": ..., "url": ..., ...}, ... ] }
music_queues: dict[int, list[dict]] = {}


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _fetch_audio_info(query: str) -> dict | None:
    """
    Resolve *query* (search term or URL) to a streamable audio dict via yt-dlp.

    Returns a dict with keys ``title``, ``url``, ``webpage_url``, ``duration``,
    or ``None`` on failure.
    """
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: _ytdl.extract_info(
                query if query.startswith("http") else f"ytsearch:{query}",
                download=False,
            ),
        )
        if "entries" in data:          # playlist / search result list
            data = data["entries"][0]
        return {
            "title":       data.get("title", "Unknown"),
            "url":         data["url"],
            "webpage_url": data.get("webpage_url", ""),
            "duration":    data.get("duration", 0),
        }
    except Exception as e:
        print(f"  [yt-dlp] {e}")
        return None


async def _play_audio(
    vc: discord.VoiceClient,
    info: dict,
    guild_id: int,
    text_channel: discord.TextChannel,
):
    """Start playback of *info* on *vc* and register the after-callback."""
    try:
        source = discord.FFmpegPCMAudio(
            info["url"], executable=FFMPEG_PATH, **FFMPEG_OPTIONS
        )
        source = discord.PCMVolumeTransformer(source, volume=0.5)

        # Build duration string
        duration_str = ""
        if info.get("duration"):
            mins, secs   = divmod(info["duration"], 60)
            duration_str = f" • {mins}:{secs:02d}"

        await text_channel.send(
            f"▶️ **Now Playing**\n"
            f"🎵 **{info['title']}**{duration_str}\n"
            f"🔗 {info.get('webpage_url', '')}"
        )

        def _after(error):
            if error:
                print(f"  [Music] Player error: {error}")
            asyncio.run_coroutine_threadsafe(
                _play_next(vc, guild_id, text_channel),
                vc.loop,
            )

        vc.play(source, after=_after)

    except Exception as e:
        await text_channel.send(f"❌ Playback error: {e}")


async def _play_next(
    vc: discord.VoiceClient,
    guild_id: int,
    text_channel: discord.TextChannel,
):
    """Play the next song in the queue, or disconnect after 5 minutes of silence."""
    queue = music_queues.get(guild_id, [])
    if queue:
        await _play_audio(vc, queue.pop(0), guild_id, text_channel)
    else:
        await text_channel.send(
            "✅ **Queue finished!**  Add more with `@Agent play <song>`."
        )
        await asyncio.sleep(300)
        if vc.is_connected() and not vc.is_playing():
            await vc.disconnect()


# ── Public API ─────────────────────────────────────────────────────────────────

async def play(
    guild_id: int,
    voice_channel: discord.VoiceChannel,
    text_channel: discord.TextChannel,
    query: str,
    bot,
):
    """
    Search for *query* and start/queue playback in *voice_channel*.

    If the bot is already playing, the song is added to the queue.
    """
    music_queues.setdefault(guild_id, [])
    await text_channel.send(f"🔍 Searching for **{query}**…")

    info = await _fetch_audio_info(query)
    if not info:
        await text_channel.send("❌ Could not find that song. Try a different search.")
        return

    # Connect / move to the voice channel
    vc = discord.utils.get(bot.voice_clients, guild=voice_channel.guild)
    if not vc or not vc.is_connected():
        vc = await voice_channel.connect()
    elif vc.channel != voice_channel:
        await vc.move_to(voice_channel)

    # Queue if something is already playing
    if vc.is_playing() or vc.is_paused():
        music_queues[guild_id].append(info)
        pos = len(music_queues[guild_id])
        await text_channel.send(
            f"➕ **Added to queue** (position {pos})\n🎵 {info['title']}"
        )
        return

    await _play_audio(vc, info, guild_id, text_channel)


def pause(vc: discord.VoiceClient | None) -> str:
    """Pause the current track. Returns a status message."""
    if vc and vc.is_playing():
        vc.pause()
        return "⏸️ **Music paused.**"
    return "❌ Nothing is playing right now."


def resume(vc: discord.VoiceClient | None) -> str:
    """Resume a paused track. Returns a status message."""
    if vc and vc.is_paused():
        vc.resume()
        return "▶️ **Music resumed!**"
    return "❌ Nothing is paused."


def skip(vc: discord.VoiceClient | None) -> str:
    """Skip the current track (triggers the after-callback → plays next). Returns status."""
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        return "⏭️ **Skipped!**"
    return "❌ Nothing is playing."


async def stop(vc: discord.VoiceClient | None, guild_id: int) -> str:
    """Stop playback, clear the queue, and disconnect. Returns status."""
    if vc and vc.is_connected():
        music_queues[guild_id] = []
        await vc.disconnect()
        return "⏹️ **Music stopped and queue cleared.**"
    return "❌ I'm not in a voice channel."


def get_queue(guild_id: int, vc: discord.VoiceClient | None) -> str:
    """Return a formatted string showing the current queue."""
    queue = music_queues.get(guild_id, [])
    if not queue and (not vc or not vc.is_playing()):
        return "📭 **The queue is empty.**"

    lines = ["🎵 **Music Queue**"]
    if vc and vc.is_playing():
        lines.append("▶️ *Now playing…*")
    for i, song in enumerate(queue, 1):
        lines.append(f"{i}. {song['title']}")
    return "\n".join(lines)