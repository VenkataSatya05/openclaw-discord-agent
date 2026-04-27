# openclaw-discord-agent
An intelligent AI agent for Discord with tools like search, weather, scheduling, and automation.
# 🤖 Discord AI Agent

A smart Discord bot powered by **Ollama (Qwen)** that acts as a true AI agent — it doesn't just chat, it **actually executes tasks** like fetching live weather, searching the web, scheduling reminders, and more.

---

## ✨ Features

| Capability | Description |
|---|---|
| 🌤 Live Weather | Real-time weather for any city |
| 🔍 Web Search | Search the internet via Serper (Google-powered) |
| ⏰ Scheduler | Actually sends messages at the time you ask |
| 🧮 Calculator | Evaluates math expressions |
| 🕐 Time Lookup | Current time for any timezone |
| 🖥️ Local LLM | Runs on your machine via Ollama — no OpenAI needed |
| 💬 Context Memory | Remembers conversation per channel |

---

## 🛠️ Tech Stack

- **[discord.py](https://discordpy.readthedocs.io/)** — Discord bot framework
- **[Ollama](https://ollama.com/)** — Run Qwen LLM locally
- **[Serper.dev](https://serper.dev/)** — Google Search API (free tier)
- **[OpenWeatherMap](https://openweathermap.org/api)** — Weather API (free tier)
- **APScheduler** — Real task scheduling
- **pytz** — Timezone handling

---

## 📋 Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running
- A Discord bot token
- A free Serper.dev API key
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
pip install discord.py pytz apscheduler requests
```

### 4. Pull the Ollama model
```bash
ollama pull qwen2.5:3b
```

### 5. Create your `.env` file
Create a file named `.env` in the project root:
```env
DISCORD_TOKEN=your_discord_bot_token_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### 6. Run the agent
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
5. Under **Privileged Gateway Intents** → enable **Message Content Intent**
6. Go to **OAuth2 → URL Generator** → check `bot` → check `Send Messages`, `Read Messages`
7. Open the generated URL to invite the bot to your server

### OpenWeatherMap API Key (Free)
1. Go to [openweathermap.org](https://openweathermap.org/api)
2. Sign up for a free account
3. Go to **API Keys** → copy your key
4. Free tier gives **1000 calls/day**

### Serper API Key (Free)
1. Go to [serper.dev](https://serper.dev)
2. Sign up (no credit card needed)
3. Copy your API key from the dashboard
4. Free tier gives **2500 searches/month**

---

## 💬 Usage

Mention the bot in any Discord channel to interact with it:

| What you say | What the agent does |
|---|---|
| `@Agent weather in Hyderabad` | Fetches live weather 🌤 |
| `@Agent IPL match score yesterday` | Searches the web 🔍 |
| `@Agent remind me at 3:00 PM to drink water` | Schedules a real message ⏰ |
| `@Agent what is 235 * 48` | Calculates instantly 🧮 |
| `@Agent time in Tokyo` | Gets current time 🕐 |
| `@Agent write fibonacci in python` | Answers with code 💻 |

---

## 📁 Project Structure

```
openclaw-discord-agent/
│
├── Agent.py          # Main bot file
├── .env              # Your API keys (never committed)
├── .env.example      # Template for others
├── .gitignore        # Ignores .env, agentenv/, __pycache__/
└── README.md         # This file
```

---

## 🏗️ How It Works

```
User @mentions Agent
        │
        ▼
  ┌─────────────┐
  │   ROUTER    │  (Qwen at temp=0) decides: tool or chat?
  └─────────────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
 TOOL      CHAT
 calls     model
   │         │
   ▼         ▼
real data  direct
fetched    reply
   │
   ▼
Chat model formats
friendly response
        │
        ▼
  Discord reply
```

The agent uses a **two-step architecture**:
1. A **router** call decides whether a tool is needed
2. If yes, the tool executes and the result is fed back to the LLM for a natural response

---

## 🔒 Security Notes

- Never commit your `.env` file — it is listed in `.gitignore`
- Keep your Discord token private — regenerate it if leaked
- The bot only responds when directly `@mentioned`

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

---

## 📄 License

MIT License — free to use and modify.
