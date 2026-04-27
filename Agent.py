"""
Agent_Sam - Discord AI Agent
Uses: Ollama (Qwen via HTTP) + Wikipedia Search + OpenWeatherMap + Real Scheduler + discord.py

Install:
    pip install discord.py pytz apscheduler requests
"""
import os
import discord
import requests
import json
import re
from datetime import datetime, timedelta
import pytz
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OLLAMA_MODEL        = "qwen2.5:3b"
OLLAMA_URL          = "http://localhost:11434/api/chat"
# SERPER_API_KEY       = "647d5e5b5e76eb3604a65280d6806ed8799488a3"
BOT_NAME            = "Agent_Sam"
BOT_TIMEZONE        = "Asia/Kolkata"              # change to your timezone

# ─────────────────────────────────────────────
#  DISCORD CLIENT + SCHEDULER
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client    = discord.Client(intents=intents)
scheduler = AsyncIOScheduler(timezone=BOT_TIMEZONE)


# ─────────────────────────────────────────────
#  OLLAMA
# ─────────────────────────────────────────────

def chat_with_ollama(messages: list, temperature: float = 0.2) -> str:
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
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
#  SEARCH TOOL  (Wikipedia only — confirmed working)
# ─────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _wiki_search(query: str) -> list:
    """Full-text search across Wikipedia titles + snippets."""
    res = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 6,
        },
        headers=HEADERS,
        timeout=10,
    ).json()
    results = []
    for r in res.get("query", {}).get("search", []):
        results.append({
            "title": r["title"],
            "snippet": re.sub(r"<.*?>", "", r.get("snippet", "")),
        })
    return results


def _wiki_summary(title: str) -> str:
    """Fetch full intro summary for a Wikipedia article."""
    res = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title.replace(' ', '_'))}",
        headers=HEADERS,
        timeout=10,
    ).json()
    return res.get("extract", "")


def _wiki_sections(title: str) -> str:
    """
    Fetch raw wikitext intro section — great for list articles
    like 'Greatest of all time' that have numbered lists.
    """
    res = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "format": "json",
        },
        headers=HEADERS,
        timeout=10,
    ).json()
    pages = res.get("query", {}).get("pages", {})
    for page in pages.values():
        return page.get("extract", "")
    return ""


def _bing_search(query: str) -> list:
    """Bing HTML scrape — fallback when Wikipedia has no good match."""
    try:
        encoded = requests.utils.quote(query)
        res = requests.get(
            f"https://www.bing.com/search?q={encoded}&cc=IN",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/124.0.0.0 Safari/537.36",
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


async def search_web_chrome(query: str) -> str:
    """
    Multi-source search:
      1. Wikipedia full-text search
      2. Wikipedia article summary for top hit
      3. Wikipedia extended extract (catches list articles)
      4. Bing HTML scrape as final fallback
    """
    print(f"  🌐 Searching: '{query}'")
    results = []

    # ── 1. Wikipedia search ────────────────────────────────────────────────
    try:
        wiki_results = _wiki_search(query)
        if wiki_results:
            print(f"  ✅ Wikipedia search: {len(wiki_results)} hits")
            results.extend(wiki_results)
    except Exception as e:
        print(f"  Wikipedia search error: {e}")

    # ── 2. Enrich top result with full summary ─────────────────────────────
    if results:
        try:
            summary = _wiki_summary(results[0]["title"])
            if summary:
                results[0]["snippet"] = summary
                print("  ✅ Wikipedia summary fetched")
        except Exception as e:
            print(f"  Wikipedia summary error: {e}")

    # ── 3. Extended extract for list/GOAT articles ─────────────────────────
    #    If query looks like a list/ranking query, also pull the section text
    list_keywords = ["top", "best", "greatest", "list", "ranking", "all time",
                     "history", "richest", "largest", "most", "famous"]
    if any(kw in query.lower() for kw in list_keywords) and results:
        try:
            extract = _wiki_sections(results[0]["title"])
            if extract and len(extract) > len(results[0]["snippet"]):
                results[0]["snippet"] = extract[:1500]   # cap at 1500 chars
                print("  ✅ Wikipedia extract fetched")
        except Exception as e:
            print(f"  Wikipedia extract error: {e}")

    # ── 4. Bing fallback ───────────────────────────────────────────────────
    if not results:
        print("  Trying Bing...")
        bing = _bing_search(query)
        if bing:
            print(f"  ✅ Bing: {len(bing)} results")
            results.extend(bing)

    # ── Build output ───────────────────────────────────────────────────────
    if not results:
        print("  ❌ All sources failed")
        return "SEARCH_FAILED"

    out = f"🔍 **Results for:** {query}\n\n"
    for i, r in enumerate(results[:5], 1):
        title   = r.get("title", "").strip()
        snippet = r.get("snippet", "").strip()
        if title or snippet:
            out += f"**{i}. {title}**\n{snippet}\n\n"

    print(f"  ✅ Final result length: {len(out)} chars")
    return out.strip()


# ─────────────────────────────────────────────
#  WEATHER TOOL
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
#  TIME TOOL
# ─────────────────────────────────────────────

def get_time(timezone: str = "Asia/Kolkata") -> str:
    try:
        tz  = pytz.timezone(timezone)
        now = datetime.now(tz)
        return f"🕐 **{timezone}**: {now.strftime('%I:%M %p, %A %d %B %Y')}"
    except Exception as e:
        return f"Time error: {e}"


# ─────────────────────────────────────────────
#  CALCULATE TOOL
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
#  SCHEDULE TOOL
# ─────────────────────────────────────────────

def schedule_message(channel_id: str, user_id: str, message: str, time_str: str) -> str:
    try:
        tz  = pytz.timezone(BOT_TIMEZONE)
        now = datetime.now(tz)
        time_str = time_str.strip()
        run_time = None

        for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M"]:
            try:
                parsed = datetime.strptime(time_str.upper(), fmt.upper())
                run_time = now.replace(
                    hour=parsed.hour, minute=parsed.minute,
                    second=0, microsecond=0,
                )
                break
            except Exception:
                continue

        if not run_time:
            return f"❌ Could not parse time '{time_str}'. Use format like '2:30 PM' or '14:30'."

        if run_time <= now:
            run_time += timedelta(days=1)

        job_id = f"msg_{channel_id}_{user_id}_{run_time.strftime('%H%M')}"
        scheduler.add_job(
            send_scheduled_message,
            "date",
            run_date=run_time,
            args=[int(channel_id), int(user_id), message],
            id=job_id,
            replace_existing=True,
        )

        formatted_time = run_time.strftime("%I:%M %p on %A %d %B")
        print(f"⏰ Scheduled job {job_id} at {run_time}")
        return f"✅ **Reminder scheduled!** I will message you at **{formatted_time}** ({BOT_TIMEZONE})."

    except Exception as e:
        return f"Schedule error: {e}"


async def send_scheduled_message(channel_id: int, user_id: int, message: str):
    try:
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(f"⏰ <@{user_id}> **Scheduled reminder:** {message}")
            print(f"✅ Sent scheduled message to channel {channel_id}")
        else:
            print(f"❌ Channel {channel_id} not found")
    except Exception as e:
        print(f"❌ Failed to send scheduled message: {e}")


# ─────────────────────────────────────────────
#  CREATE SERVER TOOL
# ─────────────────────────────────────────────

async def create_discord_server(name: str) -> str:
    try:
        guild  = await client.create_guild(name=name)
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
#  TOOL REGISTRY
# ─────────────────────────────────────────────

TOOLS = {
    "get_weather":      {"description": "Get live weather for any city",                              "params": "city (string)"},
    "search_web":       {"description": "Search internet for news, facts, rankings, current events",  "params": "query (string)"},
    "get_time":         {"description": "Get current time for a timezone",                            "params": "timezone (string)"},
    "calculate":        {"description": "Calculate a math expression",                                "params": "expression (string)"},
    "schedule_message": {"description": "Schedule a real message/reminder at a specific time",        "params": "channel_id, user_id, message, time_str"},
    "create_server":    {"description": "Create a new Discord server with a given name",              "params": "name (string)"},
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
- Weather questions → get_weather
- Sports, news, scores, IPL, rankings, "top N", "best", "latest", "history", "current events" → search_web
- Time/date questions → get_time
- Math → calculate
- "remind me at", "message me at", "notify me at" → schedule_message
- "create a server", "make a server" → create_server
- Code help, explanations, general chat → NO_TOOL

Output ONLY raw JSON or NO_TOOL. No extra text.

Examples:
{{"tool": "get_weather", "args": {{"city": "Bangalore"}}}}
{{"tool": "search_web", "args": {{"query": "top 10 athletes of all time"}}}}
{{"tool": "search_web", "args": {{"query": "top 10 companies by net worth 2026"}}}}
{{"tool": "schedule_message", "args": {{"channel_id": "CHANNEL_ID", "user_id": "USER_ID", "message": "reminder text", "time_str": "12:43 PM"}}}}
{{"tool": "create_server", "args": {{"name": "My Server"}}}}
NO_TOOL
"""

CHAT_PROMPT = f"""You are {BOT_NAME}, a helpful Discord AI assistant.
Use emojis and Discord markdown. Be concise and friendly.
When given live search/wiki data, summarize it clearly and accurately.
If the data contains a list, present it as a numbered list.
IMPORTANT: If data says SEARCH_FAILED → tell user honestly you could not fetch it.
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
#  AGENT BRAIN
# ─────────────────────────────────────────────

async def run_agent(user_message: str, history: list, message: discord.Message) -> str:
    channel_id = str(message.channel.id)
    user_id    = str(message.author.id)

    # Step 1: Route
    router_reply = chat_with_ollama(
        messages=[
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.0,
    )
    print(f"🔀 Router: {router_reply}")

    # Step 2: Execute tool
    tool_result = None

    if "NO_TOOL" not in router_reply.upper():
        data = extract_json(router_reply)

        if data:
            tool_name = data.get("tool")
            args      = data.get("args", {})
            print(f"🔧 Tool: {tool_name}({args})")

            if tool_name == "search_web":
                tool_result = await search_web_chrome(args.get("query", user_message))

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

    # Step 3: Keyword fallback → search
    if tool_result is None:
        msg_lower = user_message.lower()
        search_kw = [
            "score", "match", "ipl", "cricket", "football", "nba", "yesterday",
            "today", "latest", "recent", "news", "price", "stock", "winner",
            "result", "top", "best", "greatest", "richest", "list", "ranking",
            "history", "who is", "what is", "capital", "population",
        ]
        if any(kw in msg_lower for kw in search_kw):
            print("⚡ Keyword fallback → search")
            tool_result = await search_web_chrome(user_message.strip())

    # Step 4: Final reply
    if tool_result:
        print(f"✅ Tool result: {str(tool_result)[:120]}...")
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

    # Step 5: Pure chat
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


@client.event
async def on_ready():
    scheduler.start()
    print(f"✅ {BOT_NAME} online as {client.user}")
    print(f"🤖 Model    : {OLLAMA_MODEL}")
    print(f"🌐 Search   : Wikipedia + Bing fallback")
    print(f"⏰ Scheduler: running ({BOT_TIMEZONE})")
    print(f"🔧 Tools    : {', '.join(TOOLS.keys())}")
    print("─" * 40)


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if client.user not in message.mentions:
        return

    user_input = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not user_input:
        await message.reply(f"Hey! I'm {BOT_NAME} 👋 Ask me anything!")
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
#  RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Starting {BOT_NAME}...")
    print("─" * 40)
    client.run(DISCORD_TOKEN)