# 🤖 Discord AI Agent — Full Version

A powerful, feature-rich Discord bot powered by **Ollama (Qwen)** that acts as a true AI agent — it doesn't just chat, it **executes real tasks**: live weather, web search, music playback, games, reminders, moderation, XP leveling, and much more.

---

## ✨ Features

| Category | Capability | Description |
|---|---|---|
| 🌤 **Info** | Live Weather | Real-time weather for any city via OpenWeatherMap |
| 🔍 **Search** | Web Search | Wikipedia → Bing fallback for news, facts, scores |
| ⏰ **Scheduler** | Reminders | Sends timed messages at the exact time you ask |
| 🧮 **Math** | Calculator | Evaluates math expressions safely |
| 🕐 **Time** | Time Lookup | Current time for any timezone |
| 🖥️ **AI** | Local LLM | Runs on your machine via Ollama — no OpenAI needed |
| 💬 **Memory** | Context Memory | Remembers conversation per channel |
| 🎵 **Music** | Voice Playback | Play, pause, skip, queue music from YouTube via yt-dlp |
| 🎮 **Games** | Mini-Games | Rock Paper Scissors, Number Guess, Trivia, Truth or Dare |
| 😂 **Fun** | Jokes & Roasts | Dad jokes, dark humor, Magic 8-Ball, memes, roasts |
| 🏆 **Leveling** | XP System | Earn XP per message, level up, view leaderboard |
| 🛡️ **Moderation** | Auto-filter | Bad word detection → auto-delete + warning system |
| 🛡️ **Moderation** | Warn / Mute / Purge | Mod commands with permission checks |
| 🌐 **Server** | Create Server | Create a new Discord server with invite link |

---

## 🛠️ Tech Stack

- **[discord.py](https://discordpy.readthedocs.io/)** — Discord bot framework
- **[Ollama](https://ollama.com/)** — Run Qwen LLM locally (no OpenAI needed)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — YouTube audio streaming for music
- **[FFmpeg](https://ffmpeg.org/)** — Audio processing for voice playback
- **[OpenWeatherMap](https://openweathermap.org/api)** — Weather API (free tier)
- **Wikipedia API + Bing** — Two-stage web search (no paid key needed)
- **APScheduler** — Real task scheduling
- **pytz** — Timezone handling
- **PyNaCl** — Discord voice encryption

---

## 📋 Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running
- [FFmpeg](https://ffmpeg.org/download.html) installed (required for music)
- A Discord bot token
- A free OpenWeatherMap API key

---

## ⚙️ Setup

### 1. Clone the repository
```bash
git clone https://github.com/VenkataSatya05/openclaw-discord-agent.git
cd openclaw-discord-agent
```

### 2. Create a virtual environment
```bash
python -m venv agentenv

# Windows
agentenv\Scripts\activate

# Mac/Linux
source agentenv/bin/activate
```

### 3. Install dependencies
```bash
pip install discord.py pytz apscheduler requests python-dotenv yt-dlp PyNaCl
```

### 4. Install FFmpeg (required for music)
```bash
# Windows (via winget)
winget install ffmpeg

# Or download from https://ffmpeg.org/download.html
# Extract and add the bin/ folder to your system PATH
```

> **Note:** If FFmpeg is not on your system PATH, update the `FFMPEG_PATH` variable in `Agent.py` to point to your `ffmpeg.exe` directly.

### 5. Pull the Ollama model
```bash
ollama pull qwen2.5:3b
```

### 6. Create your `.env` file
Create a file named `.env` in the project root:
```env
DISCORD_TOKEN=your_discord_bot_token_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

### 7. Run the agent
```bash
# Make sure Ollama is running first
ollama serve

# Then in a new terminal
python Agent.py
```

---

## 🔑 Getting API Keys

### Discord Bot Token
1. Go to [discord.dev/applications](https://discord.com/developers/applications)
2. Click **New Application** → give it a name
3. Go to **Bot** → click **Add Bot**
4. Under **Token** → click **Reset Token** → copy it
5. Under **Privileged Gateway Intents** → enable **Message Content Intent** and **Server Members Intent**
6. Go to **OAuth2 → URL Generator** → check `bot` → check required permissions (see below)
7. Open the generated URL to invite the bot to your server

**Required Bot Permissions:**
- Send Messages, Read Messages/View Channels
- Manage Messages (for purge & bad word filter)
- Manage Roles (for mute)
- Connect + Speak (for music)

### OpenWeatherMap API Key (Free)
1. Go to [openweathermap.org](https://openweathermap.org/api)
2. Sign up for a free account
3. Go to **API Keys** → copy your key
4. Free tier gives **1,000 calls/day**

> **Web Search** uses Wikipedia and Bing scraping — no additional API keys needed.

---

## 💬 Usage

Mention the bot in any Discord channel:

### 🌤 Weather & Info
| What you say | What happens |
|---|---|
| `@Agent weather in Hyderabad` | Fetches live weather 🌤 |
| `@Agent time in Tokyo` | Gets current time in any timezone 🕐 |
| `@Agent what is 235 * 48` | Calculates instantly 🧮 |
| `@Agent who won the IPL 2024` | Searches the web 🔍 |

### 🎵 Music (voice channel required)
| What you say | What happens |
|---|---|
| `@Agent play Blinding Lights` | Joins your voice channel and plays the song |
| `@Agent pause` | Pauses current track |
| `@Agent resume` | Resumes playback |
| `@Agent skip` | Skips to next song in queue |
| `@Agent stop music` | Stops playback and disconnects |
| `@Agent show queue` | Lists upcoming songs |

You can also use prefix commands: `!play`, `!pause`, `!resume`, `!skip`, `!stop`, `!queue`

### 😂 Fun & Games
| What you say | What happens |
|---|---|
| `@Agent tell me a dad joke` | Delivers a dad joke with spoiler punchline 👨 |
| `@Agent dark joke` | Dark humor (spoiler-tagged) 😈 |
| `@Agent magic 8 will I pass my exam?` | Magic 8-Ball answer 🎱 |
| `@Agent roast me` / `@Agent roast John` | Burns the target 🔥 |
| `@Agent send a meme` | Random meme image 😂 |
| `@Agent play trivia` | Starts a trivia question game 🎯 |
| `@Agent play rock paper scissors` | Classic RPS game ✊✋✌️ |
| `@Agent number guess` | Guess a number 1–100 🔢 |
| `@Agent truth or dare` | Random truth + dare combo 🎭 |

### 🏆 XP & Levels
| What you say | What happens |
|---|---|
| `@Agent my level` | Shows your XP, level, and progress bar |
| `@Agent leaderboard` | Top 10 members by XP in the server |
| *(any message in server)* | Earns +10 XP automatically |

Use prefix commands: `!level`, `!leaderboard`

### 🛡️ Moderation *(requires permissions)*
| What you say | What happens |
|---|---|
| `@Agent warn John spamming` | Issues a warning (needs Manage Messages) |
| `@Agent mute John 10 bad behavior` | Mutes for 10 minutes (needs Manage Roles) |
| `@Agent purge 20` | Deletes last 20 messages (needs Manage Messages) |
| *(any message with bad words)* | Auto-deleted + warning sent, 3 strikes tracked |

Use prefix commands: `!warn @user reason`, `!mute @user minutes reason`, `!purge amount`

### ⏰ Reminders
| What you say | What happens |
|---|---|
| `@Agent remind me at 3:00 PM to drink water` | Schedules a real reminder ⏰ |

---

## 🏗️ How It Works

```
User @mentions Agent
        │
        ▼
  ┌─────────────┐
  │   ROUTER    │  (Qwen at temp=0) decides: which tool or plain chat?
  └─────────────┘
        │
   ┌────┴────────────────┐
   │                     │
   ▼                     ▼
 TOOL                  CHAT
 executes              model
   │                     │
   ▼                     ▼
real data            direct
fetched              reply
   │
   ▼
Chat model formats
friendly response
        │
        ▼
  Discord reply
```

The agent uses a **two-step architecture**:
1. A **router LLM call** (temperature 0) decides which tool to use, or `NO_TOOL` for plain chat
2. If a tool runs, its output is fed back to the LLM which formats a friendly Discord response
3. A **keyword fallback** catches search-intent messages the router might miss

---

## 📁 Project Structure

```
discord_agent/
├── main.py              ← Bot entry point, Discord events & all prefix commands
├── agent.py             ← The "brain" — routes messages, dispatches tools, builds replies
├── config.py            ← All constants & env vars in one place
├── requirements.txt
├── .env.example
├── utils/
│   ├── llm.py           ← Ollama API wrapper
│   ├── search.py        ← Wikipedia → Bing search
│   └── router.py        ← Tool registry, LLM prompts, JSON extractor
└── cogs/
    ├── info.py          ← Weather, time, calculator, scheduler, server creation
    ├── music.py         ← yt-dlp playback, queue management
    ├── fun.py           ← Jokes, Magic 8-Ball, roasts, memes, all mini-games
    ├── leveling.py      ← XP system, level-up, leaderboard
    └── moderation.py    ← Bad-word filter, warn, mute, purge
```

---

## ⚙️ Configuration

Edit these variables at the top of `Agent.py`:

```python
OLLAMA_MODEL  = "qwen2.5:3b"          # Change to any Ollama model
BOT_NAME      = "Agent"               # Bot's display name
BOT_TIMEZONE  = "Asia/Kolkata"        # Default timezone for reminders
FFMPEG_PATH   = r"C:\path\to\ffmpeg"  # Full path if ffmpeg not on PATH
```

---

## 🔒 Security Notes

- Never commit your `.env` file — it is listed in `.gitignore`
- Keep your Discord token private — regenerate it immediately if leaked
- The bot only responds when directly `@mentioned` (no passive listening for chat)
- Moderation commands are permission-gated — only users with the right Discord roles can use them
- `BAD_WORDS` list in `Agent.py` can be extended to suit your server's rules

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

MIT License — free to use and modify.
