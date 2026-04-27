# """
# Discord AI Agent
# Uses: Ollama (Qwen via HTTP) + Wikipedia + Bing + OpenWeatherMap + Music (yt-dlp)

# Install:
#     pip install discord.py pytz apscheduler requests python-dotenv yt-dlp PyNaCl

# FFmpeg (required for music):
#     Windows: winget install ffmpeg
#     OR download from https://ffmpeg.org/download.html → add bin/ to PATH

# .env file:
#     DISCORD_TOKEN=your_token
#     OPENWEATHER_API_KEY=your_key
# """

# import os
# import discord
# from discord.ext import commands
# import requests
# import json
# import re
# from datetime import datetime, timedelta
# import pytz
# import asyncio
# import time
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from dotenv import load_dotenv
# import yt_dlp

# load_dotenv()

# # ─────────────────────────────────────────────
# #  CONFIG
# # ─────────────────────────────────────────────
# DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
# OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
# OLLAMA_MODEL        = "qwen2.5:3b"
# OLLAMA_URL          = "http://localhost:11434/api/chat"
# BOT_NAME            = "Agent"
# BOT_TIMEZONE        = "Asia/Kolkata"

# # ─────────────────────────────────────────────
# #  YT-DLP OPTIONS (for music)
# # ─────────────────────────────────────────────
# YTDL_OPTIONS = {
#     "format":         "bestaudio/best",
#     "noplaylist":     True,
#     "quiet":          True,
#     "no_warnings":    True,
#     "default_search": "ytsearch",
#     "source_address": "0.0.0.0",
# }

# FFMPEG_PATH = r"C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"

# FFMPEG_OPTIONS = {
#     "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
#     "options":        "-vn",
# }

# ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# # ─────────────────────────────────────────────
# #  DISCORD CLIENT (commands.Bot needed for music)
# # ─────────────────────────────────────────────
# intents = discord.Intents.default()
# intents.message_content = True
# intents.guilds          = True
# intents.voice_states    = True

# bot       = commands.Bot(command_prefix="!", intents=intents)
# scheduler = AsyncIOScheduler(timezone=BOT_TIMEZONE)

# # Per-guild music queues
# music_queues: dict = {}

# HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# # ─────────────────────────────────────────────
# #  OLLAMA
# # ─────────────────────────────────────────────

# def chat_with_ollama(messages: list, temperature: float = 0.2) -> str:
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
#         return "ERROR: Cannot connect to Ollama. Run `ollama serve`."
#     except Exception as e:
#         return f"ERROR: {e}"


# # ─────────────────────────────────────────────
# #  SEARCH — Wikipedia + Bing fallback
# # ─────────────────────────────────────────────

# def _search_wiki(query: str) -> list:
#     try:
#         res = requests.get(
#             "https://en.wikipedia.org/w/api.php",
#             params={"action": "query", "list": "search", "srsearch": query,
#                     "format": "json", "srlimit": 6},
#             headers=HEADERS, timeout=10,
#         ).json()
#         return [{"title": r["title"],
#                  "snippet": re.sub(r"<.*?>", "", r.get("snippet", ""))}
#                 for r in res.get("query", {}).get("search", [])]
#     except Exception as e:
#         print(f"  Wikipedia search error: {e}")
#         return []


# def _wiki_summary(title: str) -> str:
#     try:
#         res = requests.get(
#             f"https://en.wikipedia.org/api/rest_v1/page/summary/"
#             f"{requests.utils.quote(title.replace(' ', '_'))}",
#             headers=HEADERS, timeout=10,
#         ).json()
#         return res.get("extract", "")
#     except Exception as e:
#         print(f"  Wikipedia summary error: {e}")
#         return ""


# def _wiki_extract(title: str) -> str:
#     try:
#         res = requests.get(
#             "https://en.wikipedia.org/w/api.php",
#             params={"action": "query", "titles": title, "prop": "extracts",
#                     "exintro": True, "explaintext": True, "format": "json"},
#             headers=HEADERS, timeout=10,
#         ).json()
#         for page in res.get("query", {}).get("pages", {}).values():
#             return page.get("extract", "")
#     except Exception as e:
#         print(f"  Wikipedia extract error: {e}")
#     return ""


# def _search_bing(query: str) -> list:
#     try:
#         res = requests.get(
#             f"https://www.bing.com/search?q={requests.utils.quote(query)}&cc=IN",
#             headers={
#                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                               "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
#                 "Accept-Language": "en-US,en;q=0.9",
#             },
#             timeout=15,
#         )
#         titles   = re.findall(r"<h2><a[^>]*>(.*?)</a></h2>", res.text, re.DOTALL)
#         snippets = re.findall(r'<div class="b_caption"><p>(.*?)</p>', res.text, re.DOTALL)
#         titles   = [re.sub(r"<.*?>", "", t).strip() for t in titles]
#         snippets = [re.sub(r"<.*?>", "", s).strip() for s in snippets]
#         results  = []
#         for i in range(min(len(titles), len(snippets), 5)):
#             if titles[i]:
#                 results.append({"title": titles[i], "snippet": snippets[i]})
#         return results
#     except Exception as e:
#         print(f"  Bing error: {e}")
#         return []


# async def search_web(query: str) -> str:
#     print(f"  🌐 Searching: '{query}'")
#     results = []
#     source  = ""

#     print("  Trying Wikipedia...")
#     wiki_results = _search_wiki(query)
#     if wiki_results:
#         print(f"  ✅ Wikipedia: {len(wiki_results)} hits")
#         results = wiki_results
#         source  = "Wikipedia"
#         summary = _wiki_summary(results[0]["title"])
#         if summary:
#             results[0]["snippet"] = summary
#         list_kw = ["top", "best", "greatest", "list", "ranking", "all time",
#                    "richest", "largest", "most", "famous", "history",
#                    "winners", "world cup", "champion"]
#         if any(kw in query.lower() for kw in list_kw):
#             extract = _wiki_extract(results[0]["title"])
#             if extract and len(extract) > len(results[0]["snippet"]):
#                 results[0]["snippet"] = extract[:1500]

#     if not results:
#         print("  Trying Bing...")
#         bing_results = _search_bing(query)
#         if bing_results:
#             print(f"  ✅ Bing: {len(bing_results)} results")
#             results = bing_results
#             source  = "Bing"

#     if not results:
#         print("  ❌ All search sources failed")
#         return "SEARCH_FAILED"

#     out = f"🔍 **Results for:** {query}\n_(via {source})_\n\n"
#     for i, r in enumerate(results[:5], 1):
#         title   = r.get("title", "").strip()
#         snippet = r.get("snippet", "").strip()
#         if title or snippet:
#             out += f"**{i}. {title}**\n{snippet}\n\n"
#     print(f"  ✅ {source}: {len(out)} chars")
#     return out.strip()


# # ─────────────────────────────────────────────
# #  WEATHER
# # ─────────────────────────────────────────────

# def get_weather(city: str) -> str:
#     try:
#         res = requests.get(
#             "https://api.openweathermap.org/data/2.5/weather",
#             params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
#             timeout=10,
#         ).json()
#         if res.get("cod") != 200:
#             return f"City '{city}' not found."
#         return (
#             f"🌤 **Weather in {city.title()}**\n"
#             f"🌡 Temp: {res['main']['temp']}°C (feels like {res['main']['feels_like']}°C)\n"
#             f"💧 Humidity: {res['main']['humidity']}%\n"
#             f"💨 Wind: {res['wind']['speed']} m/s\n"
#             f"📋 {res['weather'][0]['description'].capitalize()}"
#         )
#     except Exception as e:
#         return f"Weather error: {e}"


# # ─────────────────────────────────────────────
# #  TIME
# # ─────────────────────────────────────────────

# def get_time(timezone: str = "Asia/Kolkata") -> str:
#     try:
#         tz  = pytz.timezone(timezone)
#         now = datetime.now(tz)
#         return f"🕐 **{timezone}**: {now.strftime('%I:%M %p, %A %d %B %Y')}"
#     except Exception as e:
#         return f"Time error: {e}"


# # ─────────────────────────────────────────────
# #  CALCULATE
# # ─────────────────────────────────────────────

# def calculate(expression: str) -> str:
#     try:
#         if not all(c in "0123456789+-*/(). " for c in expression):
#             return "❌ Invalid expression."
#         return f"🧮 **{expression} = {eval(expression)}**"
#     except ZeroDivisionError:
#         return "❌ Division by zero!"
#     except Exception as e:
#         return f"Calc error: {e}"


# # ─────────────────────────────────────────────
# #  SCHEDULER
# # ─────────────────────────────────────────────

# def schedule_message(channel_id: str, user_id: str, message: str, time_str: str) -> str:
#     try:
#         tz       = pytz.timezone(BOT_TIMEZONE)
#         now      = datetime.now(tz)
#         run_time = None
#         for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M"]:
#             try:
#                 parsed   = datetime.strptime(time_str.strip().upper(), fmt.upper())
#                 run_time = now.replace(hour=parsed.hour, minute=parsed.minute,
#                                        second=0, microsecond=0)
#                 break
#             except Exception:
#                 continue
#         if not run_time:
#             return f"❌ Could not parse time '{time_str}'. Use format like '2:30 PM' or '14:30'."
#         if run_time <= now:
#             run_time += timedelta(days=1)
#         job_id = f"msg_{channel_id}_{user_id}_{run_time.strftime('%H%M')}"
#         scheduler.add_job(
#             send_scheduled_message, "date", run_date=run_time,
#             args=[int(channel_id), int(user_id), message],
#             id=job_id, replace_existing=True,
#         )
#         print(f"⏰ Scheduled: {job_id} at {run_time}")
#         return f"✅ **Reminder scheduled!** I'll message you at **{run_time.strftime('%I:%M %p on %A %d %B')}** ({BOT_TIMEZONE})."
#     except Exception as e:
#         return f"Schedule error: {e}"


# async def send_scheduled_message(channel_id: int, user_id: int, message: str):
#     try:
#         channel = bot.get_channel(channel_id)
#         if channel:
#             await channel.send(f"⏰ <@{user_id}> **Reminder:** {message}")
#             print(f"✅ Sent scheduled message to {channel_id}")
#     except Exception as e:
#         print(f"❌ Scheduled message failed: {e}")


# # ─────────────────────────────────────────────
# #  CREATE SERVER
# # ─────────────────────────────────────────────

# async def create_discord_server(name: str) -> str:
#     try:
#         guild  = await bot.create_guild(name=name)
#         invite = None
#         for channel in guild.text_channels:
#             try:
#                 invite = await channel.create_invite(max_age=0, max_uses=0)
#                 break
#             except Exception:
#                 continue
#         result = f"✅ **Server '{guild.name}' created!**\n🆔 ID: {guild.id}"
#         if invite:
#             result += f"\n🔗 Invite: {invite.url}"
#         return result
#     except discord.Forbidden:
#         return "❌ No permission to create servers."
#     except Exception as e:
#         return f"Server creation error: {e}"


# # ─────────────────────────────────────────────
# #  🎵 MUSIC FUNCTIONS
# # ─────────────────────────────────────────────

# async def _fetch_audio(query: str) -> dict | None:
#     """Fetch audio stream URL from YouTube using yt-dlp."""
#     try:
#         loop = asyncio.get_event_loop()
#         data = await loop.run_in_executor(
#             None,
#             lambda: ytdl.extract_info(
#                 query if query.startswith("http") else f"ytsearch:{query}",
#                 download=False
#             )
#         )
#         if "entries" in data:
#             data = data["entries"][0]
#         return {
#             "title":       data.get("title", "Unknown"),
#             "url":         data["url"],
#             "webpage_url": data.get("webpage_url", ""),
#             "duration":    data.get("duration", 0),
#         }
#     except Exception as e:
#         print(f"  yt-dlp error: {e}")
#         return None


# async def music_play(guild_id: int, voice_channel: discord.VoiceChannel,
#                      text_channel: discord.TextChannel, query: str):
#     """Join voice and play audio. Queue if already playing."""
#     try:
#         if guild_id not in music_queues:
#             music_queues[guild_id] = []

#         await text_channel.send(f"🔍 Searching for **{query}**...")

#         info = await _fetch_audio(query)
#         if not info:
#             await text_channel.send("❌ Could not find that song. Try a different search.")
#             return

#         # Connect or move to voice channel
#         vc = discord.utils.get(bot.voice_clients, guild=voice_channel.guild)
#         if not vc or not vc.is_connected():
#             vc = await voice_channel.connect()
#         elif vc.channel != voice_channel:
#             await vc.move_to(voice_channel)

#         # Add to queue if already playing
#         if vc.is_playing() or vc.is_paused():
#             music_queues[guild_id].append(info)
#             pos = len(music_queues[guild_id])
#             await text_channel.send(
#                 f"➕ **Added to queue** (position {pos})\n🎵 {info['title']}"
#             )
#             return

#         await _play_audio(vc, info, guild_id, text_channel)

#     except discord.ClientException as e:
#         await text_channel.send(f"❌ Voice error: {e}")
#     except Exception as e:
#         await text_channel.send(f"❌ Error: {e}")
#         print(f"  music_play error: {e}")


# async def _play_audio(vc: discord.VoiceClient, info: dict,
#                       guild_id: int, text_channel: discord.TextChannel):
#     """Play audio and auto-advance queue when done."""
#     try:
#         source = discord.FFmpegPCMAudio(info["url"], executable=FFMPEG_PATH, **FFMPEG_OPTIONS)
#         source = discord.PCMVolumeTransformer(source, volume=0.5)

#         duration_str = ""
#         if info.get("duration"):
#             mins, secs   = divmod(info["duration"], 60)
#             duration_str = f" • {mins}:{secs:02d}"

#         await text_channel.send(
#             f"▶️ **Now Playing**\n"
#             f"🎵 **{info['title']}**{duration_str}\n"
#             f"🔗 {info.get('webpage_url', '')}"
#         )

#         def after_playing(error):
#             if error:
#                 print(f"  Player error: {error}")
#             asyncio.run_coroutine_threadsafe(
#                 _play_next(vc, guild_id, text_channel), bot.loop
#             )

#         vc.play(source, after=after_playing)

#     except Exception as e:
#         await text_channel.send(f"❌ Playback error: {e}")
#         print(f"  _play_audio error: {e}")


# async def _play_next(vc: discord.VoiceClient, guild_id: int,
#                      text_channel: discord.TextChannel):
#     """Play next in queue or disconnect after 5 min idle."""
#     queue = music_queues.get(guild_id, [])
#     if queue:
#         next_song = queue.pop(0)
#         await _play_audio(vc, next_song, guild_id, text_channel)
#     else:
#         await text_channel.send("✅ **Queue finished!** Use `@Agent play <song>` to add more.")
#         await asyncio.sleep(300)
#         if vc.is_connected() and not vc.is_playing():
#             await vc.disconnect()


# # ─────────────────────────────────────────────
# #  TOOL REGISTRY
# # ─────────────────────────────────────────────

# TOOLS = {
#     "get_weather":      {"description": "Get live weather for any city",                            "params": "city (string)"},
#     "search_web":       {"description": "Search internet for news, scores, facts, current events",  "params": "query (string)"},
#     "get_time":         {"description": "Get current time for a timezone",                          "params": "timezone (string)"},
#     "calculate":        {"description": "Calculate a math expression",                              "params": "expression (string)"},
#     "schedule_message": {"description": "Schedule a real message/reminder at a specific time",      "params": "channel_id, user_id, message, time_str"},
#     "create_server":    {"description": "Create a new Discord server with a given name",            "params": "name (string)"},
#     "play_music":       {"description": "Play a song or YouTube video in voice channel",            "params": "query (string)"},
#     "pause_music":      {"description": "Pause the currently playing music",                        "params": "none"},
#     "resume_music":     {"description": "Resume paused music",                                      "params": "none"},
#     "skip_music":       {"description": "Skip current song and play next in queue",                 "params": "none"},
#     "stop_music":       {"description": "Stop music and leave voice channel",                       "params": "none"},
#     "show_queue":       {"description": "Show the current music queue",                             "params": "none"},
# }

# TOOL_DESCRIPTIONS = "\n".join(
#     [f"- {name}({v['params']}): {v['description']}" for name, v in TOOLS.items()]
# )


# # ─────────────────────────────────────────────
# #  PROMPTS
# # ─────────────────────────────────────────────

# ROUTER_PROMPT = f"""You are a tool router. Output ONLY a JSON tool call or NO_TOOL.

# Tools:
# {TOOL_DESCRIPTIONS}

# ROUTING RULES:
# - Weather → get_weather
# - Sports, news, scores, IPL, cricket, "top N", "best", "latest", "history", current events → search_web
# - Time/date → get_time
# - Math → calculate
# - "remind me at", "message me at", "notify me at" → schedule_message
# - "create a server", "make a server" → create_server
# - "play [song/artist]", "play music" → play_music
# - "pause", "pause music" → pause_music
# - "resume", "continue music" → resume_music
# - "skip", "next song" → skip_music
# - "stop music", "leave voice", "disconnect" → stop_music
# - "queue", "what's playing", "song list" → show_queue
# - Code help, explanations, general chat → NO_TOOL

# Output ONLY raw JSON or NO_TOOL. No extra text. Examples:
# {{"tool": "get_weather",      "args": {{"city": "Bangalore"}}}}
# {{"tool": "search_web",       "args": {{"query": "IPL match score yesterday 2026"}}}}
# {{"tool": "play_music",       "args": {{"query": "Believer Imagine Dragons"}}}}
# {{"tool": "schedule_message", "args": {{"channel_id": "CHANNEL_ID", "user_id": "USER_ID", "message": "drink water", "time_str": "3:00 PM"}}}}
# NO_TOOL
# """

# CHAT_PROMPT = f"""You are {BOT_NAME}, a helpful Discord AI assistant.
# Use emojis and Discord markdown. Be concise and friendly.
# When given live search data, summarize it clearly and accurately.
# If data contains a numbered list, present it as a numbered list.
# IMPORTANT: If data says SEARCH_FAILED → tell the user honestly you could not fetch it.
# DO NOT guess or make up any facts, numbers, or scores.
# """


# # ─────────────────────────────────────────────
# #  JSON EXTRACTOR
# # ─────────────────────────────────────────────

# def extract_json(text: str):
#     try:
#         return json.loads(text.strip())
#     except Exception:
#         pass
#     m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
#     if m:
#         try:
#             return json.loads(m.group(1))
#         except Exception:
#             pass
#     m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
#     if m:
#         try:
#             return json.loads(m.group())
#         except Exception:
#             pass
#     return None


# # ─────────────────────────────────────────────
# #  AGENT BRAIN
# # ─────────────────────────────────────────────

# async def run_agent(user_message: str, history: list, message: discord.Message) -> str:
#     channel_id = str(message.channel.id)
#     user_id    = str(message.author.id)
#     guild_id   = message.guild.id if message.guild else None

#     # Step 1: Route
#     router_reply = chat_with_ollama(
#         messages=[
#             {"role": "system", "content": ROUTER_PROMPT},
#             {"role": "user",   "content": user_message},
#         ],
#         temperature=0.0,
#     )
#     print(f"🔀 Router: {router_reply}")

#     tool_result = None

#     # Step 2: Execute tool
#     if "NO_TOOL" not in router_reply.upper():
#         data = extract_json(router_reply)

#         if data:
#             tool_name = data.get("tool")
#             args      = data.get("args", {})
#             print(f"🔧 Tool: {tool_name}({args})")

#             # ── 🎵 Music tools ────────────────────────────────
#             if tool_name == "play_music" and guild_id:
#                 if not message.author.voice:
#                     return "❌ You need to **join a voice channel** first, then ask me to play!"
#                 asyncio.create_task(
#                     music_play(guild_id, message.author.voice.channel,
#                                message.channel, args.get("query", ""))
#                 )
#                 return f"🎵 Looking up **{args.get('query', '')}**..."

#             elif tool_name == "pause_music" and guild_id:
#                 vc = discord.utils.get(bot.voice_clients, guild=message.guild)
#                 if vc and vc.is_playing():
#                     vc.pause()
#                     return "⏸️ **Music paused.** Say `@Agent resume` to continue."
#                 return "❌ Nothing is playing right now."

#             elif tool_name == "resume_music" and guild_id:
#                 vc = discord.utils.get(bot.voice_clients, guild=message.guild)
#                 if vc and vc.is_paused():
#                     vc.resume()
#                     return "▶️ **Music resumed!**"
#                 return "❌ Nothing is paused."

#             elif tool_name == "skip_music" and guild_id:
#                 vc = discord.utils.get(bot.voice_clients, guild=message.guild)
#                 if vc and (vc.is_playing() or vc.is_paused()):
#                     vc.stop()
#                     return "⏭️ **Skipped!** Playing next song..."
#                 return "❌ Nothing is playing."

#             elif tool_name == "stop_music" and guild_id:
#                 vc = discord.utils.get(bot.voice_clients, guild=message.guild)
#                 if vc and vc.is_connected():
#                     music_queues[guild_id] = []
#                     await vc.disconnect()
#                     return "⏹️ **Music stopped.** Disconnected from voice channel."
#                 return "❌ I'm not in a voice channel."

#             elif tool_name == "show_queue" and guild_id:
#                 queue = music_queues.get(guild_id, [])
#                 vc    = discord.utils.get(bot.voice_clients, guild=message.guild)
#                 if not queue and (not vc or not vc.is_playing()):
#                     return "📭 **Queue is empty.** Say `@Agent play <song>` to add music!"
#                 out = "🎵 **Music Queue**\n"
#                 if vc and vc.is_playing():
#                     out += "▶️ **Now playing** (current song)\n"
#                 for i, song in enumerate(queue, 1):
#                     out += f"{i}. {song['title']}\n"
#                 return out

#             # ── Other tools ───────────────────────────────────
#             elif tool_name == "search_web":
#                 tool_result = await search_web(args.get("query", user_message))

#             elif tool_name == "schedule_message":
#                 args["channel_id"] = channel_id
#                 args["user_id"]    = user_id
#                 tool_result = schedule_message(**args)

#             elif tool_name == "create_server":
#                 tool_result = await create_discord_server(**args)

#             elif tool_name == "get_weather":
#                 tool_result = get_weather(**args)

#             elif tool_name == "get_time":
#                 tool_result = get_time(**args)

#             elif tool_name == "calculate":
#                 tool_result = calculate(**args)

#     # Step 3: Keyword fallback for missed searches
#     if tool_result is None:
#         msg_lower = user_message.lower()
#         search_kw = [
#             "score", "match", "ipl", "cricket", "football", "nba", "yesterday",
#             "today", "latest", "recent", "news", "price", "stock", "winner",
#             "result", "top", "best", "greatest", "richest", "list", "ranking",
#             "history", "who is", "what is", "capital", "population",
#             "world cup", "how many", "when did", "who won",
#         ]
#         if any(kw in msg_lower for kw in search_kw):
#             print("⚡ Keyword fallback → search_web")
#             tool_result = await search_web(user_message.strip())

#     # Step 4: Final reply
#     if tool_result:
#         print(f"✅ Tool result: {str(tool_result)[:120]}...")
#         history.append({"role": "user", "content": user_message})
#         history.append({
#             "role": "user",
#             "content": f"Tool data:\n\n{tool_result}\n\nRespond to the user based on this data.",
#         })
#         reply = chat_with_ollama(
#             messages=[{"role": "system", "content": CHAT_PROMPT}] + history,
#             temperature=0.7,
#         )
#         history.append({"role": "assistant", "content": reply})
#         return reply

#     # Step 5: Pure chat
#     history.append({"role": "user", "content": user_message})
#     reply = chat_with_ollama(
#         messages=[{"role": "system", "content": CHAT_PROMPT}] + history,
#         temperature=0.7,
#     )
#     history.append({"role": "assistant", "content": reply})
#     return reply


# # ─────────────────────────────────────────────
# #  DISCORD EVENTS
# # ─────────────────────────────────────────────

# conversation_history: dict = {}
# MAX_HISTORY = 10


# @bot.event
# async def on_ready():
#     scheduler.start()
#     print(f"✅ {BOT_NAME} online as {bot.user}")
#     print(f"🤖 Model    : {OLLAMA_MODEL}")
#     print(f"🌐 Search   : Wikipedia → Bing (auto-fallback)")
#     print(f"🎵 Music    : yt-dlp ready")
#     print(f"⏰ Scheduler: running ({BOT_TIMEZONE})")
#     print(f"🔧 Tools    : {', '.join(TOOLS.keys())}")
#     print("─" * 40)


# @bot.event
# async def on_message(message: discord.Message):
#     if message.author == bot.user:
#         return

#     await bot.process_commands(message)  # allow !play etc.

#     if bot.user not in message.mentions:
#         return

#     user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
#     if not user_input:
#         await message.reply(
#             f"Hey! I'm **{BOT_NAME}** 👋\n"
#             f"I can help with weather, search, music, reminders, math and more!\n"
#             f"🎵 Try: `@{BOT_NAME} play Believer by Imagine Dragons`"
#         )
#         return

#     print(f"\n📨 {message.author}: {user_input}")

#     async with message.channel.typing():
#         channel_id = str(message.channel.id)
#         if channel_id not in conversation_history:
#             conversation_history[channel_id] = []
#         history = conversation_history[channel_id]

#         try:
#             reply = await run_agent(user_input, history, message)
#         except Exception as e:
#             reply = f"⚠️ Error: {e}"
#             print(f"❌ {e}")

#         if len(history) > MAX_HISTORY * 2:
#             conversation_history[channel_id] = history[-(MAX_HISTORY * 2):]

#         if len(reply) > 1900:
#             for chunk in [reply[i:i + 1900] for i in range(0, len(reply), 1900)]:
#                 await message.reply(chunk)
#         else:
#             await message.reply(reply)


# # ─────────────────────────────────────────────
# #  PREFIX COMMANDS (shortcuts for music)
# # ─────────────────────────────────────────────

# @bot.command(name="play")
# async def cmd_play(ctx, *, query: str):
#     """!play <song name or YouTube URL>"""
#     if not ctx.author.voice:
#         await ctx.send("❌ Join a voice channel first!")
#         return
#     await music_play(ctx.guild.id, ctx.author.voice.channel, ctx.channel, query)


# @bot.command(name="pause")
# async def cmd_pause(ctx):
#     vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
#     if vc and vc.is_playing():
#         vc.pause()
#         await ctx.send("⏸️ Paused.")
#     else:
#         await ctx.send("❌ Nothing playing.")


# @bot.command(name="resume")
# async def cmd_resume(ctx):
#     vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
#     if vc and vc.is_paused():
#         vc.resume()
#         await ctx.send("▶️ Resumed!")
#     else:
#         await ctx.send("❌ Nothing paused.")


# @bot.command(name="skip")
# async def cmd_skip(ctx):
#     vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
#     if vc and vc.is_playing():
#         vc.stop()
#         await ctx.send("⏭️ Skipped!")
#     else:
#         await ctx.send("❌ Nothing playing.")


# @bot.command(name="stop")
# async def cmd_stop(ctx):
#     vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
#     if vc:
#         music_queues[ctx.guild.id] = []
#         await vc.disconnect()
#         await ctx.send("⏹️ Stopped and disconnected.")
#     else:
#         await ctx.send("❌ Not in a voice channel.")


# @bot.command(name="queue")
# async def cmd_queue(ctx):
#     queue = music_queues.get(ctx.guild.id, [])
#     if not queue:
#         await ctx.send("📭 Queue is empty.")
#         return
#     out = "🎵 **Queue:**\n"
#     for i, s in enumerate(queue, 1):
#         out += f"{i}. {s['title']}\n"
#     await ctx.send(out)


# # ─────────────────────────────────────────────
# #  RUN
# # ─────────────────────────────────────────────

# if __name__ == "__main__":
#     print(f"🚀 Starting {BOT_NAME}...")
#     print("─" * 40)
#     bot.run(DISCORD_TOKEN)


"""
Discord AI Agent - Full Version
Features: Weather, Search, Music, Reminders, Math, Games/Fun, Moderation

Install:
    pip install discord.py pytz apscheduler requests python-dotenv yt-dlp PyNaCl

FFmpeg (required for music):
    Windows: winget install ffmpeg
    OR download from https://ffmpeg.org/download.html → add bin/ to PATH

.env file:
    DISCORD_TOKEN=your_token
    OPENWEATHER_API_KEY=your_key
"""

import os
import discord
from discord.ext import commands
import requests
import json
import re
import random
from datetime import datetime, timedelta
import pytz
import asyncio
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OLLAMA_MODEL        = "qwen2.5:3b"
OLLAMA_URL          = "http://localhost:11434/api/chat"
BOT_NAME            = "Agent"
BOT_TIMEZONE        = "Asia/Kolkata"

# ─── UPDATE THIS PATH if ffmpeg is not on system PATH ───
FFMPEG_PATH = r"C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"

# ─────────────────────────────────────────────
#  YT-DLP OPTIONS
# ─────────────────────────────────────────────
YTDL_OPTIONS = {
    "format":         "bestaudio/best",
    "noplaylist":     True,
    "quiet":          True,
    "no_warnings":    True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options":        "-vn",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ─────────────────────────────────────────────
#  DISCORD CLIENT
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds          = True
intents.voice_states    = True
intents.members         = True   # needed for moderation

bot       = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone=BOT_TIMEZONE)

# Per-guild music queues
music_queues: dict = {}

# Per-user game states  {channel_id: {user_id: game_state}}
game_states: dict = {}

# Per-guild warnings    {guild_id: {user_id: count}}
user_warnings: dict = {}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ─────────────────────────────────────────────
#  BAD WORDS LIST  (extend as needed)
# ─────────────────────────────────────────────
BAD_WORDS = [
    "fuck", "shit", "bitch", "asshole", "bastard", "damn", "crap",
    "piss", "dick", "cock", "pussy", "nigger", "nigga", "faggot",
    "retard", "whore", "slut", "cunt", "motherfucker", "bullshit",
]

def contains_bad_word(text: str) -> str | None:
    """Returns the matched bad word or None."""
    lower = text.lower()
    for word in BAD_WORDS:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, lower):
            return word
    return None


# ─────────────────────────────────────────────
#  OLLAMA
# ─────────────────────────────────────────────

def chat_with_ollama(messages: list, temperature: float = 0.2) -> str:
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
        return "ERROR: Cannot connect to Ollama. Run `ollama serve`."
    except Exception as e:
        return f"ERROR: {e}"


# ─────────────────────────────────────────────
#  SEARCH — Wikipedia + Bing fallback
# ─────────────────────────────────────────────

def _search_wiki(query: str) -> list:
    try:
        res = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query,
                    "format": "json", "srlimit": 6},
            headers=HEADERS, timeout=10,
        ).json()
        return [{"title": r["title"],
                 "snippet": re.sub(r"<.*?>", "", r.get("snippet", ""))}
                for r in res.get("query", {}).get("search", [])]
    except Exception as e:
        print(f"  Wikipedia search error: {e}")
        return []


def _wiki_summary(title: str) -> str:
    try:
        res = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/"
            f"{requests.utils.quote(title.replace(' ', '_'))}",
            headers=HEADERS, timeout=10,
        ).json()
        return res.get("extract", "")
    except Exception as e:
        print(f"  Wikipedia summary error: {e}")
        return ""


def _wiki_extract(title: str) -> str:
    try:
        res = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": title, "prop": "extracts",
                    "exintro": True, "explaintext": True, "format": "json"},
            headers=HEADERS, timeout=10,
        ).json()
        for page in res.get("query", {}).get("pages", {}).values():
            return page.get("extract", "")
    except Exception as e:
        print(f"  Wikipedia extract error: {e}")
    return ""


def _search_bing(query: str) -> list:
    try:
        res = requests.get(
            f"https://www.bing.com/search?q={requests.utils.quote(query)}&cc=IN",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
        )
        titles   = re.findall(r"<h2><a[^>]*>(.*?)</a></h2>", res.text, re.DOTALL)
        snippets = re.findall(r'<div class="b_caption"><p>(.*?)</p>', res.text, re.DOTALL)
        titles   = [re.sub(r"<.*?>", "", t).strip() for t in titles]
        snippets = [re.sub(r"<.*?>", "", s).strip() for s in snippets]
        results  = []
        for i in range(min(len(titles), len(snippets), 5)):
            if titles[i]:
                results.append({"title": titles[i], "snippet": snippets[i]})
        return results
    except Exception as e:
        print(f"  Bing error: {e}")
        return []


async def search_web(query: str) -> str:
    print(f"  🌐 Searching: '{query}'")
    results = []
    source  = ""

    wiki_results = _search_wiki(query)
    if wiki_results:
        results = wiki_results
        source  = "Wikipedia"
        summary = _wiki_summary(results[0]["title"])
        if summary:
            results[0]["snippet"] = summary
        list_kw = ["top", "best", "greatest", "list", "ranking", "all time",
                   "richest", "largest", "most", "famous", "history",
                   "winners", "world cup", "champion"]
        if any(kw in query.lower() for kw in list_kw):
            extract = _wiki_extract(results[0]["title"])
            if extract and len(extract) > len(results[0]["snippet"]):
                results[0]["snippet"] = extract[:1500]

    if not results:
        bing_results = _search_bing(query)
        if bing_results:
            results = bing_results
            source  = "Bing"

    if not results:
        return "SEARCH_FAILED"

    out = f"🔍 **Results for:** {query}\n_(via {source})_\n\n"
    for i, r in enumerate(results[:5], 1):
        title   = r.get("title", "").strip()
        snippet = r.get("snippet", "").strip()
        if title or snippet:
            out += f"**{i}. {title}**\n{snippet}\n\n"
    return out.strip()


# ─────────────────────────────────────────────
#  WEATHER
# ─────────────────────────────────────────────

def get_weather(city: str) -> str:
    try:
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        ).json()
        if res.get("cod") != 200:
            return f"City '{city}' not found."
        return (
            f"🌤 **Weather in {city.title()}**\n"
            f"🌡 Temp: {res['main']['temp']}°C (feels like {res['main']['feels_like']}°C)\n"
            f"💧 Humidity: {res['main']['humidity']}%\n"
            f"💨 Wind: {res['wind']['speed']} m/s\n"
            f"📋 {res['weather'][0]['description'].capitalize()}"
        )
    except Exception as e:
        return f"Weather error: {e}"


# ─────────────────────────────────────────────
#  TIME
# ─────────────────────────────────────────────

def get_time(timezone: str = "Asia/Kolkata") -> str:
    try:
        tz  = pytz.timezone(timezone)
        now = datetime.now(tz)
        return f"🕐 **{timezone}**: {now.strftime('%I:%M %p, %A %d %B %Y')}"
    except Exception as e:
        return f"Time error: {e}"


# ─────────────────────────────────────────────
#  CALCULATE
# ─────────────────────────────────────────────

def calculate(expression: str) -> str:
    try:
        if not all(c in "0123456789+-*/(). " for c in expression):
            return "❌ Invalid expression."
        return f"🧮 **{expression} = {eval(expression)}**"
    except ZeroDivisionError:
        return "❌ Division by zero!"
    except Exception as e:
        return f"Calc error: {e}"


# ─────────────────────────────────────────────
#  SCHEDULER
# ─────────────────────────────────────────────

def schedule_message(channel_id: str, user_id: str, message: str, time_str: str) -> str:
    try:
        tz       = pytz.timezone(BOT_TIMEZONE)
        now      = datetime.now(tz)
        run_time = None
        for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M"]:
            try:
                parsed   = datetime.strptime(time_str.strip().upper(), fmt.upper())
                run_time = now.replace(hour=parsed.hour, minute=parsed.minute,
                                       second=0, microsecond=0)
                break
            except Exception:
                continue
        if not run_time:
            return f"❌ Could not parse time '{time_str}'. Use format like '2:30 PM' or '14:30'."
        if run_time <= now:
            run_time += timedelta(days=1)
        job_id = f"msg_{channel_id}_{user_id}_{run_time.strftime('%H%M')}"
        scheduler.add_job(
            send_scheduled_message, "date", run_date=run_time,
            args=[int(channel_id), int(user_id), message],
            id=job_id, replace_existing=True,
        )
        return f"✅ **Reminder scheduled!** I'll message you at **{run_time.strftime('%I:%M %p on %A %d %B')}** ({BOT_TIMEZONE})."
    except Exception as e:
        return f"Schedule error: {e}"


async def send_scheduled_message(channel_id: int, user_id: int, message: str):
    try:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(f"⏰ <@{user_id}> **Reminder:** {message}")
    except Exception as e:
        print(f"❌ Scheduled message failed: {e}")


# ─────────────────────────────────────────────
#  CREATE SERVER
# ─────────────────────────────────────────────

async def create_discord_server(name: str) -> str:
    try:
        guild  = await bot.create_guild(name=name)
        invite = None
        for channel in guild.text_channels:
            try:
                invite = await channel.create_invite(max_age=0, max_uses=0)
                break
            except Exception:
                continue
        result = f"✅ **Server '{guild.name}' created!**\n🆔 ID: {guild.id}"
        if invite:
            result += f"\n🔗 Invite: {invite.url}"
        return result
    except discord.Forbidden:
        return "❌ No permission to create servers."
    except Exception as e:
        return f"Server creation error: {e}"


# ─────────────────────────────────────────────
#  🎮 GAMES & FUN TOOLS
# ─────────────────────────────────────────────

JOKES = [
    ("Why don't scientists trust atoms?", "Because they make up everything! 😄"),
    ("Why did the scarecrow win an award?", "Because he was outstanding in his field! 🌾"),
    ("I told my wife she was drawing her eyebrows too high.", "She looked surprised. 😲"),
    ("Why don't eggs tell jokes?", "They'd crack each other up! 🥚"),
    ("What do you call fake spaghetti?", "An impasta! 🍝"),
    ("Why did the math book look so sad?", "Because it had too many problems. 📚"),
    ("What did the ocean say to the beach?", "Nothing, it just waved. 🌊"),
    ("I'm reading a book about anti-gravity.", "It's impossible to put down! 📖"),
    ("Why can't your nose be 12 inches long?", "Because then it'd be a foot! 👃"),
    ("What do you call cheese that isn't yours?", "Nacho cheese! 🧀"),
]

DAD_JOKES = [
    ("I used to hate facial hair...", "but then it grew on me. 🧔"),
    ("Why did the bicycle fall over?", "Because it was two-tired! 🚲"),
    ("What time did the man go to the dentist?", "Tooth-hurty! 🦷"),
    ("I'm on a seafood diet.", "I see food and I eat it. 🍔"),
    ("What do you call a sleeping dinosaur?", "A dino-snore! 🦕"),
]

DARK_JOKES = [
    "I told a joke about paper. It was tearable. 📄",
    "My wife told me I had to stop acting like a flamingo. I had to put my foot down. 🦩",
    "I asked my dog what two minus two is. He said nothing. 🐕",
    "Why don't graveyards ever get overcrowded? Because people are dying to get in. ⚰️",
]

MAGIC_8_RESPONSES = [
    "🎱 **It is certain.**",
    "🎱 **It is decidedly so.**",
    "🎱 **Without a doubt.**",
    "🎱 **Yes, definitely.**",
    "🎱 **You may rely on it.**",
    "🎱 **As I see it, yes.**",
    "🎱 **Most likely.**",
    "🎱 **Outlook good.**",
    "🎱 **Yes.**",
    "🎱 **Signs point to yes.**",
    "🎱 **Reply hazy, try again.**",
    "🎱 **Ask again later.**",
    "🎱 **Better not tell you now.**",
    "🎱 **Cannot predict now.**",
    "🎱 **Concentrate and ask again.**",
    "🎱 **Don't count on it.**",
    "🎱 **My reply is no.**",
    "🎱 **My sources say no.**",
    "🎱 **Outlook not so good.**",
    "🎱 **Very doubtful.**",
]

ROASTS = [
    "You're like a cloud ☁️ — when you disappear, it's a beautiful day.",
    "I'd roast you, but my mom said I'm not allowed to burn trash. 🗑️",
    "You have your entire life to be an idiot. Why not take today off? 😴",
    "I'm not saying you're dumb, but you'd have to study hard to become an idiot. 📚",
    "You're the reason they put instructions on shampoo bottles. 🧴",
    "I'd explain it to you, but I don't have any crayons with me. 🖍️",
    "You're like a software update. Whenever I see you, I think 'Not now.' 💻",
    "I was going to tell you a joke about your life… but I see it's already one. 😂",
]

TRIVIA_QUESTIONS = [
    {"q": "What planet is closest to the Sun?", "a": "mercury", "hint": "It's tiny and rocky 🪨"},
    {"q": "How many continents are there on Earth?", "a": "7", "hint": "More than 6, less than 8 🌍"},
    {"q": "What is the capital of France?", "a": "paris", "hint": "City of Lights 🗼"},
    {"q": "Who painted the Mona Lisa?", "a": "da vinci", "hint": "Italian Renaissance genius 🎨"},
    {"q": "What is the chemical symbol for gold?", "a": "au", "hint": "From the Latin 'Aurum' ✨"},
    {"q": "How many sides does a hexagon have?", "a": "6", "hint": "Like a honeycomb 🐝"},
    {"q": "What is the largest ocean on Earth?", "a": "pacific", "hint": "Its name means peaceful 🌊"},
    {"q": "In what year did World War II end?", "a": "1945", "hint": "Mid-40s 📅"},
    {"q": "What is the fastest land animal?", "a": "cheetah", "hint": "Big spotted cat 🐆"},
    {"q": "How many bones are in the adult human body?", "a": "206", "hint": "Between 200 and 210 🦴"},
]

TRUTH_OR_DARE_TRUTHS = [
    "What's the most embarrassing thing you've ever done? 😳",
    "What's a secret you've never told anyone in this server? 🤫",
    "Who was your first crush? 💘",
    "What's the worst lie you've ever told? 🤥",
    "What's your biggest fear? 😨",
    "Have you ever cheated on a test? 📝",
    "What's the most childish thing you still do? 🧸",
    "What's your most embarrassing username from the past? 💻",
]

TRUTH_OR_DARE_DARES = [
    "Send the last photo in your camera roll! 📸",
    "Type with your nose for your next message! 👃",
    "Say something nice about everyone currently online in this server! 💬",
    "Change your nickname to 'PotatoHead' for 10 minutes! 🥔",
    "Send a voice message of you singing your favorite song for 10 seconds! 🎤",
    "Write a poem about the last person who messaged in this chat! 📜",
    "Type your next 3 messages using only emojis! 🎭",
    "Tell us your most embarrassing autocorrect fail! 📱",
]

MEME_TEMPLATES = [
    "https://i.imgflip.com/4t0m5.jpg",   # Drake
    "https://i.imgflip.com/1bij.jpg",    # One does not simply
    "https://i.imgflip.com/1otk96.jpg",  # Two buttons
    "https://i.imgflip.com/9ehk.jpg",    # Distracted boyfriend
    "https://i.imgflip.com/1g8my4.jpg",  # Mocking SpongeBob
    "https://i.imgflip.com/2hgfw.jpg",   # Change my mind
]


def tell_joke(joke_type: str = "random") -> str:
    joke_type = joke_type.lower()
    if "dad" in joke_type:
        setup, punchline = random.choice(DAD_JOKES)
        return f"👨 **Dad Joke Time!**\n\n*{setup}*\n\n||{punchline}||"
    elif "dark" in joke_type:
        return f"😈 **Dark Humor Warning:**\n\n||{random.choice(DARK_JOKES)}||"
    else:
        setup, punchline = random.choice(JOKES)
        return f"😂 **Here's a joke!**\n\n*{setup}*\n\n||{punchline}||"


def magic_8ball(question: str = "") -> str:
    response = random.choice(MAGIC_8_RESPONSES)
    if question:
        return f"🎱 **Question:** {question}\n\n{response}"
    return response


def roast(target: str = "you") -> str:
    roast_text = random.choice(ROASTS)
    return f"🔥 **Roast for {target}:**\n\n{roast_text}"


def get_meme() -> str:
    url = random.choice(MEME_TEMPLATES)
    return f"😂 **Random Meme!**\n{url}"


def start_game(game_type: str, channel_id: str, user_id: str) -> str:
    """Start a mini-game and return the opening message."""
    game_type = game_type.lower()

    if "rock" in game_type or "rps" in game_type or "paper" in game_type:
        game_states.setdefault(channel_id, {})[user_id] = {"type": "rps"}
        return (
            "✊✋✌️ **Rock, Paper, Scissors!**\n\n"
            "Reply with: `rock`, `paper`, or `scissors`"
        )

    elif "number" in game_type or "guess" in game_type:
        number = random.randint(1, 100)
        game_states.setdefault(channel_id, {})[user_id] = {
            "type": "number_guess", "number": number, "attempts": 0
        }
        return (
            "🔢 **Number Guessing Game!**\n\n"
            "I'm thinking of a number between **1 and 100**.\n"
            "Type your guess!"
        )

    elif "trivia" in game_type:
        q = random.choice(TRIVIA_QUESTIONS)
        game_states.setdefault(channel_id, {})[user_id] = {
            "type": "trivia", "answer": q["a"], "hint": q["hint"]
        }
        return f"🎯 **Trivia Time!**\n\n**Q:** {q['q']}\n\n*(Type your answer or say 'hint')*"

    elif "truth" in game_type or "dare" in game_type:
        truth = random.choice(TRUTH_OR_DARE_TRUTHS)
        dare  = random.choice(TRUTH_OR_DARE_DARES)
        return (
            f"🎭 **Truth or Dare?**\n\n"
            f"**TRUTH:** {truth}\n\n"
            f"**DARE:** {dare}\n\n"
            f"*Choose your fate!*"
        )

    else:
        # Random game picker
        games = ["rps", "number guess", "trivia", "truth or dare"]
        chosen = random.choice(games)
        return start_game(chosen, channel_id, user_id)


def process_game_input(user_input: str, channel_id: str, user_id: str) -> str | None:
    """Process game reply. Returns response or None if no active game."""
    state = game_states.get(channel_id, {}).get(user_id)
    if not state:
        return None

    game_type = state.get("type")

    # ── Rock Paper Scissors ──
    if game_type == "rps":
        choices = ["rock", "paper", "scissors"]
        user_choice = user_input.lower().strip()
        if user_choice not in choices:
            return None  # Not a game input
        bot_choice = random.choice(choices)
        emoji_map  = {"rock": "✊", "paper": "✋", "scissors": "✌️"}

        if user_choice == bot_choice:
            result = "🤝 **It's a tie!**"
        elif (user_choice == "rock"     and bot_choice == "scissors") or \
             (user_choice == "scissors" and bot_choice == "paper") or \
             (user_choice == "paper"    and bot_choice == "rock"):
            result = "🎉 **You win!**"
        else:
            result = "😈 **I win!**"

        del game_states[channel_id][user_id]
        return (
            f"{emoji_map[user_choice]} You chose **{user_choice}**\n"
            f"{emoji_map[bot_choice]} I chose **{bot_choice}**\n\n"
            f"{result}\n\nPlay again? `@{BOT_NAME} play rock paper scissors`"
        )

    # ── Number Guess ──
    elif game_type == "number_guess":
        try:
            guess = int(user_input.strip())
        except ValueError:
            return None
        state["attempts"] += 1
        number = state["number"]
        if guess == number:
            del game_states[channel_id][user_id]
            return (
                f"🎉 **CORRECT!** The number was **{number}**!\n"
                f"You got it in **{state['attempts']} attempts**! "
                + ("🏆 Amazing!" if state['attempts'] <= 5 else "Good job!")
            )
        elif guess < number:
            return f"📈 **Too low!** Try higher. *(Attempt {state['attempts']})*"
        else:
            return f"📉 **Too high!** Try lower. *(Attempt {state['attempts']})*"

    # ── Trivia ──
    elif game_type == "trivia":
        user_ans = user_input.lower().strip()
        if user_ans == "hint":
            return f"💡 **Hint:** {state['hint']}"
        correct_ans = state["answer"].lower()
        if user_ans == correct_ans or correct_ans in user_ans:
            del game_states[channel_id][user_id]
            return f"✅ **Correct!** 🎉 The answer was **{state['answer']}**!\nPlay again? `@{BOT_NAME} trivia`"
        else:
            return f"❌ **Wrong!** Try again or say `hint` for a clue."

    return None


# ─── XP / Level System ───────────────────────
user_xp: dict = {}   # {guild_id: {user_id: xp}}

XP_PER_MESSAGE  = 10
LEVEL_THRESHOLD = 100   # XP per level

def add_xp(guild_id: int, user_id: int) -> tuple[int, int, bool]:
    """Add XP and return (new_xp, level, leveled_up)."""
    guild_data = user_xp.setdefault(guild_id, {})
    guild_data[user_id] = guild_data.get(user_id, 0) + XP_PER_MESSAGE
    xp    = guild_data[user_id]
    level = xp // LEVEL_THRESHOLD
    leveled_up = (xp % LEVEL_THRESHOLD) < XP_PER_MESSAGE and xp >= LEVEL_THRESHOLD
    return xp, level, leveled_up


def show_level(guild_id: int, user_id: int, username: str) -> str:
    xp    = user_xp.get(guild_id, {}).get(user_id, 0)
    level = xp // LEVEL_THRESHOLD
    next_level_xp = (level + 1) * LEVEL_THRESHOLD
    progress  = xp % LEVEL_THRESHOLD
    bar_fill  = int((progress / LEVEL_THRESHOLD) * 10)
    bar       = "█" * bar_fill + "░" * (10 - bar_fill)
    return (
        f"⭐ **{username}'s Stats**\n"
        f"🏅 Level: **{level}**\n"
        f"✨ XP: **{xp}** / {next_level_xp}\n"
        f"📊 Progress: `[{bar}]` {progress}/{LEVEL_THRESHOLD}"
    )


def show_leaderboard(guild_id: int, guild) -> str:
    data = user_xp.get(guild_id, {})
    if not data:
        return "📭 No XP data yet. Chat more to earn XP!"
    sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    out = "🏆 **Leaderboard**\n\n"
    for i, (uid, xp) in enumerate(sorted_users):
        member = guild.get_member(uid)
        name   = member.display_name if member else f"User {uid}"
        level  = xp // LEVEL_THRESHOLD
        out += f"{medals[i]} **{name}** — Level {level} ({xp} XP)\n"
    return out


# ─────────────────────────────────────────────
#  🛡️ MODERATION TOOLS
# ─────────────────────────────────────────────

async def bad_word_filter(message: discord.Message) -> bool:
    """
    Check message for bad words. Delete and warn if found.
    Returns True if message was deleted.
    """
    matched = contains_bad_word(message.content)
    if not matched:
        return False

    try:
        await message.delete()
    except discord.Forbidden:
        pass

    guild_id = message.guild.id if message.guild else 0
    user_id  = message.author.id
    user_warnings.setdefault(guild_id, {})
    user_warnings[guild_id][user_id] = user_warnings[guild_id].get(user_id, 0) + 1
    count = user_warnings[guild_id][user_id]

    warning_text = (
        f"⚠️ {message.author.mention} Watch your language! "
        f"That message was removed. **Warning {count}/3**"
    )
    if count >= 3:
        warning_text += "\n🚨 You've received **3 warnings**! Further violations may result in a mute."

    await message.channel.send(warning_text, delete_after=10)
    return True


async def warn_user(guild: discord.Guild, target_member: discord.Member,
                    reason: str, channel: discord.TextChannel) -> str:
    guild_id = guild.id
    user_id  = target_member.id
    user_warnings.setdefault(guild_id, {})
    user_warnings[guild_id][user_id] = user_warnings[guild_id].get(user_id, 0) + 1
    count = user_warnings[guild_id][user_id]

    try:
        await target_member.send(
            f"⚠️ **Warning from {guild.name}**\n"
            f"Reason: {reason}\n"
            f"Warning count: {count}/3"
        )
    except discord.Forbidden:
        pass

    return (
        f"⚠️ **{target_member.display_name}** has been warned.\n"
        f"📋 Reason: {reason}\n"
        f"🔢 Total warnings: **{count}/3**"
    )


async def mute_user(guild: discord.Guild, target_member: discord.Member,
                    duration_minutes: int, reason: str,
                    channel: discord.TextChannel) -> str:
    try:
        mute_role = discord.utils.get(guild.roles, name="Muted")
        if not mute_role:
            mute_role = await guild.create_role(name="Muted")
            for ch in guild.channels:
                try:
                    await ch.set_permissions(mute_role, send_messages=False, speak=False)
                except Exception:
                    pass

        await target_member.add_roles(mute_role, reason=reason)
        result = (
            f"🔇 **{target_member.display_name}** has been muted for **{duration_minutes} minutes**.\n"
            f"📋 Reason: {reason}"
        )

        async def unmute():
            await asyncio.sleep(duration_minutes * 60)
            try:
                await target_member.remove_roles(mute_role)
                await channel.send(f"🔊 **{target_member.display_name}** has been unmuted.")
            except Exception:
                pass

        asyncio.create_task(unmute())
        return result

    except discord.Forbidden:
        return "❌ I don't have permission to mute members. Make sure I have **Manage Roles** permission."
    except Exception as e:
        return f"Mute error: {e}"


async def purge_messages(channel: discord.TextChannel, amount: int) -> str:
    try:
        amount  = min(max(amount, 1), 100)
        deleted = await channel.purge(limit=amount)
        return f"🗑️ **Deleted {len(deleted)} messages.**"
    except discord.Forbidden:
        return "❌ I don't have **Manage Messages** permission."
    except Exception as e:
        return f"Purge error: {e}"


# ─────────────────────────────────────────────
#  🎵 MUSIC FUNCTIONS
# ─────────────────────────────────────────────

async def _fetch_audio(query: str) -> dict | None:
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(
                query if query.startswith("http") else f"ytsearch:{query}",
                download=False
            )
        )
        if "entries" in data:
            data = data["entries"][0]
        return {
            "title":       data.get("title", "Unknown"),
            "url":         data["url"],
            "webpage_url": data.get("webpage_url", ""),
            "duration":    data.get("duration", 0),
        }
    except Exception as e:
        print(f"  yt-dlp error: {e}")
        return None


async def music_play(guild_id: int, voice_channel: discord.VoiceChannel,
                     text_channel: discord.TextChannel, query: str):
    try:
        if guild_id not in music_queues:
            music_queues[guild_id] = []

        await text_channel.send(f"🔍 Searching for **{query}**...")

        info = await _fetch_audio(query)
        if not info:
            await text_channel.send("❌ Could not find that song. Try a different search.")
            return

        vc = discord.utils.get(bot.voice_clients, guild=voice_channel.guild)
        if not vc or not vc.is_connected():
            vc = await voice_channel.connect()
        elif vc.channel != voice_channel:
            await vc.move_to(voice_channel)

        if vc.is_playing() or vc.is_paused():
            music_queues[guild_id].append(info)
            pos = len(music_queues[guild_id])
            await text_channel.send(f"➕ **Added to queue** (position {pos})\n🎵 {info['title']}")
            return

        await _play_audio(vc, info, guild_id, text_channel)

    except discord.ClientException as e:
        await text_channel.send(f"❌ Voice error: {e}")
    except Exception as e:
        await text_channel.send(f"❌ Error: {e}")


async def _play_audio(vc: discord.VoiceClient, info: dict,
                      guild_id: int, text_channel: discord.TextChannel):
    try:
        source = discord.FFmpegPCMAudio(info["url"], executable=FFMPEG_PATH, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=0.5)

        duration_str = ""
        if info.get("duration"):
            mins, secs   = divmod(info["duration"], 60)
            duration_str = f" • {mins}:{secs:02d}"

        await text_channel.send(
            f"▶️ **Now Playing**\n"
            f"🎵 **{info['title']}**{duration_str}\n"
            f"🔗 {info.get('webpage_url', '')}"
        )

        def after_playing(error):
            if error:
                print(f"  Player error: {error}")
            asyncio.run_coroutine_threadsafe(
                _play_next(vc, guild_id, text_channel), bot.loop
            )

        vc.play(source, after=after_playing)

    except Exception as e:
        await text_channel.send(f"❌ Playback error: {e}")


async def _play_next(vc: discord.VoiceClient, guild_id: int,
                     text_channel: discord.TextChannel):
    queue = music_queues.get(guild_id, [])
    if queue:
        next_song = queue.pop(0)
        await _play_audio(vc, next_song, guild_id, text_channel)
    else:
        await text_channel.send("✅ **Queue finished!** Use `@Agent play <song>` to add more.")
        await asyncio.sleep(300)
        if vc.is_connected() and not vc.is_playing():
            await vc.disconnect()


# ─────────────────────────────────────────────
#  TOOL REGISTRY
# ─────────────────────────────────────────────

TOOLS = {
    # Existing tools
    "get_weather":      {"description": "Get live weather for any city",                           "params": "city (string)"},
    "search_web":       {"description": "Search internet for news, scores, facts",                 "params": "query (string)"},
    "get_time":         {"description": "Get current time for a timezone",                         "params": "timezone (string)"},
    "calculate":        {"description": "Calculate a math expression",                             "params": "expression (string)"},
    "schedule_message": {"description": "Schedule a reminder at a specific time",                  "params": "channel_id, user_id, message, time_str"},
    "create_server":    {"description": "Create a new Discord server",                             "params": "name (string)"},
    "play_music":       {"description": "Play a song in voice channel",                            "params": "query (string)"},
    "pause_music":      {"description": "Pause the currently playing music",                       "params": "none"},
    "resume_music":     {"description": "Resume paused music",                                     "params": "none"},
    "skip_music":       {"description": "Skip current song",                                       "params": "none"},
    "stop_music":       {"description": "Stop music and leave voice channel",                      "params": "none"},
    "show_queue":       {"description": "Show the music queue",                                    "params": "none"},
    # Games & Fun
    "tell_joke":        {"description": "Tell a joke (random/dad/dark)",                           "params": "joke_type (string: random|dad|dark)"},
    "magic_8ball":      {"description": "Magic 8-ball answer for yes/no questions",               "params": "question (string)"},
    "roast":            {"description": "Roast a user with a funny insult",                        "params": "target (string)"},
    "meme":             {"description": "Send a random meme image",                                "params": "none"},
    "play_game":        {"description": "Start a mini-game: rps, number guess, trivia, truth or dare", "params": "game_type (string)"},
    "show_level":       {"description": "Show a user's XP level and rank",                         "params": "none"},
    # Moderation
    "bad_word_filter":  {"description": "Check and filter profanity in messages",                  "params": "none (automatic)"},
    "warn_user":        {"description": "Issue a warning to a user",                               "params": "username, reason"},
    "mute_user":        {"description": "Mute a user for N minutes",                               "params": "username, duration_minutes, reason"},
    "purge_messages":   {"description": "Delete N recent messages from channel",                   "params": "amount (int)"},
}

TOOL_DESCRIPTIONS = "\n".join(
    [f"- {name}({v['params']}): {v['description']}" for name, v in TOOLS.items()]
)


# ─────────────────────────────────────────────
#  PROMPTS
# ─────────────────────────────────────────────

ROUTER_PROMPT = f"""You are a tool router. Output ONLY a JSON tool call or NO_TOOL.

Tools:
{TOOL_DESCRIPTIONS}

ROUTING RULES:
- Weather → get_weather
- Sports, news, scores, facts, current events → search_web
- Time/date → get_time
- Math → calculate
- "remind me at", "notify me at" → schedule_message
- "create a server" → create_server
- "play [song]" → play_music
- "pause" → pause_music
- "resume" → resume_music
- "skip" → skip_music
- "stop music" → stop_music
- "queue" → show_queue
- "joke", "make me laugh", "funny", "dad joke", "dark humor" → tell_joke
- "magic 8", "will I", "should I", "yes or no" → magic_8ball
- "roast me", "roast @user" → roast
- "meme", "send meme" → meme
- "play game", "rock paper scissors", "trivia", "number guess", "truth or dare", "bored", "entertain me" → play_game
- "my level", "my rank", "my xp", "leaderboard" → show_level
- "warn @user" → warn_user
- "mute @user" → mute_user
- "purge", "delete messages", "clear chat" → purge_messages
- General chat, code help → NO_TOOL

Output ONLY raw JSON or NO_TOOL. No extra text. Examples:
{{"tool": "get_weather", "args": {{"city": "Bangalore"}}}}
{{"tool": "tell_joke", "args": {{"joke_type": "dad"}}}}
{{"tool": "magic_8ball", "args": {{"question": "Will I pass my exam?"}}}}
{{"tool": "roast", "args": {{"target": "John"}}}}
{{"tool": "play_game", "args": {{"game_type": "trivia"}}}}
{{"tool": "warn_user", "args": {{"username": "John", "reason": "spamming"}}}}
{{"tool": "mute_user", "args": {{"username": "John", "duration_minutes": 10, "reason": "bad behavior"}}}}
{{"tool": "purge_messages", "args": {{"amount": 10}}}}
NO_TOOL
"""

CHAT_PROMPT = f"""You are {BOT_NAME}, a helpful Discord AI assistant.
Use emojis and Discord markdown. Be concise and friendly.
When given live search data, summarize it clearly and accurately.
If data contains a numbered list, present it as a numbered list.
IMPORTANT: If data says SEARCH_FAILED → tell the user honestly you could not fetch it.
DO NOT guess or make up any facts, numbers, or scores.
"""


# ─────────────────────────────────────────────
#  JSON EXTRACTOR
# ─────────────────────────────────────────────

def extract_json(text: str):
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────
#  HELPER: find member by name
# ─────────────────────────────────────────────

def find_member(guild: discord.Guild, name: str) -> discord.Member | None:
    name_lower = name.lower().strip()
    for member in guild.members:
        if member.display_name.lower() == name_lower or \
           member.name.lower() == name_lower or \
           str(member.id) == name_lower:
            return member
    # fuzzy match
    for member in guild.members:
        if name_lower in member.display_name.lower() or \
           name_lower in member.name.lower():
            return member
    return None


# ─────────────────────────────────────────────
#  AGENT BRAIN
# ─────────────────────────────────────────────

async def run_agent(user_message: str, history: list, message: discord.Message) -> str:
    channel_id = str(message.channel.id)
    user_id    = str(message.author.id)
    guild_id   = message.guild.id if message.guild else None

    # ── Check active game first ──
    game_reply = process_game_input(user_message, channel_id, str(message.author.id))
    if game_reply:
        return game_reply

    # ── Route ──
    router_reply = chat_with_ollama(
        messages=[
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.0,
    )
    print(f"🔀 Router: {router_reply}")

    tool_result = None

    if "NO_TOOL" not in router_reply.upper():
        data = extract_json(router_reply)

        if data:
            tool_name = data.get("tool")
            args      = data.get("args", {})
            print(f"🔧 Tool: {tool_name}({args})")

            # ── Music ──
            if tool_name == "play_music" and guild_id:
                if not message.author.voice:
                    return "❌ You need to **join a voice channel** first!"
                asyncio.create_task(
                    music_play(guild_id, message.author.voice.channel,
                               message.channel, args.get("query", ""))
                )
                return f"🎵 Looking up **{args.get('query', '')}**..."

            elif tool_name == "pause_music" and guild_id:
                vc = discord.utils.get(bot.voice_clients, guild=message.guild)
                if vc and vc.is_playing():
                    vc.pause()
                    return "⏸️ **Music paused.**"
                return "❌ Nothing is playing."

            elif tool_name == "resume_music" and guild_id:
                vc = discord.utils.get(bot.voice_clients, guild=message.guild)
                if vc and vc.is_paused():
                    vc.resume()
                    return "▶️ **Music resumed!**"
                return "❌ Nothing is paused."

            elif tool_name == "skip_music" and guild_id:
                vc = discord.utils.get(bot.voice_clients, guild=message.guild)
                if vc and (vc.is_playing() or vc.is_paused()):
                    vc.stop()
                    return "⏭️ **Skipped!**"
                return "❌ Nothing is playing."

            elif tool_name == "stop_music" and guild_id:
                vc = discord.utils.get(bot.voice_clients, guild=message.guild)
                if vc and vc.is_connected():
                    music_queues[guild_id] = []
                    await vc.disconnect()
                    return "⏹️ **Music stopped.**"
                return "❌ Not in a voice channel."

            elif tool_name == "show_queue" and guild_id:
                queue = music_queues.get(guild_id, [])
                vc    = discord.utils.get(bot.voice_clients, guild=message.guild)
                if not queue and (not vc or not vc.is_playing()):
                    return "📭 **Queue is empty.**"
                out = "🎵 **Music Queue**\n"
                if vc and vc.is_playing():
                    out += "▶️ **Now playing** (current song)\n"
                for i, song in enumerate(queue, 1):
                    out += f"{i}. {song['title']}\n"
                return out

            # ── Games & Fun ──
            elif tool_name == "tell_joke":
                return tell_joke(args.get("joke_type", "random"))

            elif tool_name == "magic_8ball":
                return magic_8ball(args.get("question", ""))

            elif tool_name == "roast":
                target = args.get("target", message.author.display_name)
                return roast(target)

            elif tool_name == "meme":
                return get_meme()

            elif tool_name == "play_game":
                game_type = args.get("game_type", "random")
                return start_game(game_type, channel_id, str(message.author.id))

            elif tool_name == "show_level":
                msg_lower = user_message.lower()
                if "leaderboard" in msg_lower and message.guild:
                    return show_leaderboard(guild_id, message.guild)
                return show_level(guild_id, message.author.id, message.author.display_name)

            # ── Moderation ──
            elif tool_name == "warn_user" and message.guild:
                if not message.author.guild_permissions.manage_messages:
                    return "❌ You need **Manage Messages** permission to warn users."
                target = find_member(message.guild, args.get("username", ""))
                if not target:
                    return f"❌ Could not find user **{args.get('username')}**."
                reason = args.get("reason", "No reason provided")
                return await warn_user(message.guild, target, reason, message.channel)

            elif tool_name == "mute_user" and message.guild:
                if not message.author.guild_permissions.manage_roles:
                    return "❌ You need **Manage Roles** permission to mute users."
                target = find_member(message.guild, args.get("username", ""))
                if not target:
                    return f"❌ Could not find user **{args.get('username')}**."
                duration = int(args.get("duration_minutes", 10))
                reason   = args.get("reason", "No reason provided")
                return await mute_user(message.guild, target, duration, reason, message.channel)

            elif tool_name == "purge_messages" and message.guild:
                if not message.author.guild_permissions.manage_messages:
                    return "❌ You need **Manage Messages** permission to purge."
                amount = int(args.get("amount", 10))
                return await purge_messages(message.channel, amount)

            # ── Other tools ──
            elif tool_name == "search_web":
                tool_result = await search_web(args.get("query", user_message))

            elif tool_name == "schedule_message":
                args["channel_id"] = channel_id
                args["user_id"]    = user_id
                tool_result = schedule_message(**args)

            elif tool_name == "create_server":
                tool_result = await create_discord_server(**args)

            elif tool_name == "get_weather":
                tool_result = get_weather(**args)

            elif tool_name == "get_time":
                tool_result = get_time(**args)

            elif tool_name == "calculate":
                tool_result = calculate(**args)

    # ── Keyword fallback for missed searches ──
    if tool_result is None:
        msg_lower = user_message.lower()
        search_kw = [
            "score", "match", "ipl", "cricket", "football", "nba", "yesterday",
            "today", "latest", "recent", "news", "price", "stock", "winner",
            "result", "top", "best", "greatest", "richest", "list", "ranking",
            "history", "who is", "what is", "capital", "population",
            "world cup", "how many", "when did", "who won",
        ]
        if any(kw in msg_lower for kw in search_kw):
            tool_result = await search_web(user_message.strip())

    # ── Final reply ──
    if tool_result:
        history.append({"role": "user", "content": user_message})
        history.append({
            "role": "user",
            "content": f"Tool data:\n\n{tool_result}\n\nRespond to the user based on this data.",
        })
        reply = chat_with_ollama(
            messages=[{"role": "system", "content": CHAT_PROMPT}] + history,
            temperature=0.7,
        )
        history.append({"role": "assistant", "content": reply})
        return reply

    # ── Pure chat ──
    history.append({"role": "user", "content": user_message})
    reply = chat_with_ollama(
        messages=[{"role": "system", "content": CHAT_PROMPT}] + history,
        temperature=0.7,
    )
    history.append({"role": "assistant", "content": reply})
    return reply


# ─────────────────────────────────────────────
#  DISCORD EVENTS
# ─────────────────────────────────────────────

conversation_history: dict = {}
MAX_HISTORY = 10


@bot.event
async def on_ready():
    scheduler.start()
    print(f"✅ {BOT_NAME} online as {bot.user}")
    print(f"🤖 Model    : {OLLAMA_MODEL}")
    print(f"🌐 Search   : Wikipedia → Bing")
    print(f"🎵 Music    : yt-dlp ready")
    print(f"🎮 Games    : RPS, Number Guess, Trivia, Truth or Dare")
    print(f"🛡️  Moderation: Warn, Mute, Purge, Bad Word Filter")
    print(f"⏰ Scheduler: running ({BOT_TIMEZONE})")
    print(f"🔧 Tools    : {', '.join(TOOLS.keys())}")
    print("─" * 50)


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    # ── Auto bad word filter (all messages) ──
    if message.guild and not message.author.bot:
        deleted = await bad_word_filter(message)
        if deleted:
            return  # message was removed, stop processing

    # ── XP for every message in a guild ──
    if message.guild and not message.author.bot:
        xp, level, leveled_up = add_xp(message.guild.id, message.author.id)
        if leveled_up:
            await message.channel.send(
                f"🎉 {message.author.mention} leveled up to **Level {level}**! ⭐",
                delete_after=15
            )

    if bot.user not in message.mentions:
        return

    user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not user_input:
        await message.reply(
            f"Hey! I'm **{BOT_NAME}** 👋\n"
            f"**What I can do:**\n"
            f"🌤 Weather • 🔍 Search • 🎵 Music • ⏰ Reminders • 🧮 Math\n"
            f"😂 Jokes • 🎱 Magic 8-Ball • 🔥 Roast • 🎮 Games • 🏆 Levels\n"
            f"🛡️ Warn/Mute/Purge (mods only)\n\n"
            f"Try: `@{BOT_NAME} tell me a dad joke` or `@{BOT_NAME} play trivia`"
        )
        return

    print(f"\n📨 {message.author}: {user_input}")

    async with message.channel.typing():
        channel_id = str(message.channel.id)
        if channel_id not in conversation_history:
            conversation_history[channel_id] = []
        history = conversation_history[channel_id]

        try:
            reply = await run_agent(user_input, history, message)
        except Exception as e:
            reply = f"⚠️ Error: {e}"
            print(f"❌ {e}")

        if len(history) > MAX_HISTORY * 2:
            conversation_history[channel_id] = history[-(MAX_HISTORY * 2):]

        if len(reply) > 1900:
            for chunk in [reply[i:i + 1900] for i in range(0, len(reply), 1900)]:
                await message.reply(chunk)
        else:
            await message.reply(reply)


# ─────────────────────────────────────────────
#  PREFIX COMMANDS
# ─────────────────────────────────────────────

@bot.command(name="play")
async def cmd_play(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("❌ Join a voice channel first!")
        return
    await music_play(ctx.guild.id, ctx.author.voice.channel, ctx.channel, query)

@bot.command(name="pause")
async def cmd_pause(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_playing(): vc.pause(); await ctx.send("⏸️ Paused.")
    else: await ctx.send("❌ Nothing playing.")

@bot.command(name="resume")
async def cmd_resume(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_paused(): vc.resume(); await ctx.send("▶️ Resumed!")
    else: await ctx.send("❌ Nothing paused.")

@bot.command(name="skip")
async def cmd_skip(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_playing(): vc.stop(); await ctx.send("⏭️ Skipped!")
    else: await ctx.send("❌ Nothing playing.")

@bot.command(name="stop")
async def cmd_stop(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc:
        music_queues[ctx.guild.id] = []
        await vc.disconnect()
        await ctx.send("⏹️ Stopped.")
    else: await ctx.send("❌ Not in a voice channel.")

@bot.command(name="queue")
async def cmd_queue(ctx):
    queue = music_queues.get(ctx.guild.id, [])
    if not queue: await ctx.send("📭 Queue is empty."); return
    out = "🎵 **Queue:**\n"
    for i, s in enumerate(queue, 1): out += f"{i}. {s['title']}\n"
    await ctx.send(out)

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def cmd_warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    result = await warn_user(ctx.guild, member, reason, ctx.channel)
    await ctx.send(result)

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def cmd_mute(ctx, member: discord.Member, duration: int = 10, *, reason: str = "No reason"):
    result = await mute_user(ctx.guild, member, duration, reason, ctx.channel)
    await ctx.send(result)

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def cmd_purge(ctx, amount: int = 10):
    await ctx.message.delete()
    result = await purge_messages(ctx.channel, amount)
    await ctx.send(result, delete_after=5)

@bot.command(name="level")
async def cmd_level(ctx):
    await ctx.send(show_level(ctx.guild.id, ctx.author.id, ctx.author.display_name))

@bot.command(name="leaderboard")
async def cmd_leaderboard(ctx):
    await ctx.send(show_leaderboard(ctx.guild.id, ctx.guild))

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

# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Starting {BOT_NAME}...")
    print("─" * 50)
    bot.run(DISCORD_TOKEN)