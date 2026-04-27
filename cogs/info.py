"""
cogs/info.py — Informational & utility tools.

Covers: weather, time, calculator, reminder scheduler, Discord server creation.
"""

import asyncio
from datetime import datetime, timedelta

import discord
import pytz
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import OPENWEATHER_API_KEY, BOT_TIMEZONE


# ── Scheduler (shared instance, started in main.py) ───────────────────────────
scheduler = AsyncIOScheduler(timezone=BOT_TIMEZONE)


# ── Weather ────────────────────────────────────────────────────────────────────

def get_weather(city: str) -> str:
    """
    Fetch current weather for *city* from OpenWeatherMap.

    Returns a formatted Discord-ready string, or an error message.
    """
    try:
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        ).json()

        if res.get("cod") != 200:
            return f"❌ City **'{city}'** not found. Please check the spelling."

        return (
            f"🌤 **Weather in {city.title()}**\n"
            f"🌡 Temp: **{res['main']['temp']}°C** "
            f"(feels like {res['main']['feels_like']}°C)\n"
            f"💧 Humidity: {res['main']['humidity']}%\n"
            f"💨 Wind: {res['wind']['speed']} m/s\n"
            f"📋 {res['weather'][0]['description'].capitalize()}"
        )
    except Exception as e:
        return f"❌ Weather error: {e}"


# ── Time ───────────────────────────────────────────────────────────────────────

def get_time(timezone: str = "Asia/Kolkata") -> str:
    """
    Return the current time in *timezone* (IANA format, e.g. 'America/New_York').
    """
    try:
        tz  = pytz.timezone(timezone)
        now = datetime.now(tz)
        return f"🕐 **{timezone}**\n{now.strftime('%I:%M %p, %A %d %B %Y')}"
    except pytz.exceptions.UnknownTimeZoneError:
        return f"❌ Unknown timezone **'{timezone}'**. Use IANA format, e.g. `Asia/Kolkata`."
    except Exception as e:
        return f"❌ Time error: {e}"


# ── Calculator ─────────────────────────────────────────────────────────────────

_SAFE_CHARS = set("0123456789+-*/(). ")


def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression and return the result.

    Only digits, basic operators, parentheses, and spaces are allowed.
    """
    if not all(c in _SAFE_CHARS for c in expression):
        return "❌ Invalid expression — only numbers and `+ - * / ( )` are allowed."
    try:
        result = eval(expression)  # noqa: S307 — guarded by char-whitelist above
        return f"🧮 `{expression} = {result}`"
    except ZeroDivisionError:
        return "❌ Division by zero!"
    except Exception as e:
        return f"❌ Calculation error: {e}"


# ── Reminder scheduler ─────────────────────────────────────────────────────────

def schedule_message(
    channel_id: str,
    user_id: str,
    message: str,
    time_str: str,
    bot,          # discord.ext.commands.Bot — passed in to avoid circular import
) -> str:
    """
    Schedule *message* to be sent in *channel_id* at *time_str*.

    Accepts formats like ``2:30 PM``, ``2:30PM``, or ``14:30``.
    If the parsed time is in the past today, schedules for tomorrow.
    """
    try:
        tz       = pytz.timezone(BOT_TIMEZONE)
        now      = datetime.now(tz)
        run_time = None

        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
            try:
                parsed   = datetime.strptime(time_str.strip().upper(), fmt.upper())
                run_time = now.replace(
                    hour=parsed.hour, minute=parsed.minute,
                    second=0, microsecond=0,
                )
                break
            except ValueError:
                continue

        if run_time is None:
            return (
                f"❌ Could not parse time **'{time_str}'**.\n"
                "Use formats like `2:30 PM` or `14:30`."
            )

        if run_time <= now:
            run_time += timedelta(days=1)

        job_id = f"msg_{channel_id}_{user_id}_{run_time.strftime('%H%M')}"
        scheduler.add_job(
            _send_scheduled_message,
            "date",
            run_date=run_time,
            args=[bot, int(channel_id), int(user_id), message],
            id=job_id,
            replace_existing=True,
        )
        return (
            f"✅ **Reminder scheduled!**\n"
            f"I'll ping you at **{run_time.strftime('%I:%M %p on %A %d %B')}** "
            f"({BOT_TIMEZONE})."
        )
    except Exception as e:
        return f"❌ Schedule error: {e}"


async def _send_scheduled_message(bot, channel_id: int, user_id: int, message: str):
    """Callback fired by APScheduler — sends the reminder into the channel."""
    try:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(f"⏰ <@{user_id}> **Reminder:** {message}")
    except Exception as e:
        print(f"  [Scheduler] Failed to send scheduled message: {e}")


# ── Discord server creation ────────────────────────────────────────────────────

async def create_discord_server(name: str, bot) -> str:
    """
    Create a new Discord guild named *name* and return a permanent invite link.

    Note: Only bots in fewer than 10 guilds can create guilds via the API.
    """
    try:
        guild  = await bot.create_guild(name=name)
        invite = None
        for channel in guild.text_channels:
            try:
                invite = await channel.create_invite(max_age=0, max_uses=0)
                break
            except discord.Forbidden:
                continue

        result = f"✅ **Server '{guild.name}' created!**\n🆔 ID: `{guild.id}`"
        if invite:
            result += f"\n🔗 Invite: {invite.url}"
        return result

    except discord.Forbidden:
        return "❌ I don't have permission to create servers."
    except Exception as e:
        return f"❌ Server creation error: {e}"