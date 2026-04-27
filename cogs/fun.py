"""
cogs/fun.py — Games, jokes, roasts, Magic 8-Ball, memes.

All functions are synchronous (pure Python, no I/O) except where noted.
Active game states are stored in the module-level ``game_states`` dict so
they survive across multiple message events without a database.
"""

import random

# ── Static data ────────────────────────────────────────────────────────────────

_JOKES: list[tuple[str, str]] = [
    ("Why don't scientists trust atoms?",             "Because they make up everything! 😄"),
    ("Why did the scarecrow win an award?",           "Because he was outstanding in his field! 🌾"),
    ("I told my wife she was drawing her eyebrows too high.", "She looked surprised. 😲"),
    ("Why don't eggs tell jokes?",                    "They'd crack each other up! 🥚"),
    ("What do you call fake spaghetti?",              "An impasta! 🍝"),
    ("Why did the math book look so sad?",            "Because it had too many problems. 📚"),
    ("What did the ocean say to the beach?",          "Nothing, it just waved. 🌊"),
    ("I'm reading a book about anti-gravity.",        "It's impossible to put down! 📖"),
    ("Why can't your nose be 12 inches long?",        "Because then it'd be a foot! 👃"),
    ("What do you call cheese that isn't yours?",     "Nacho cheese! 🧀"),
]

_DAD_JOKES: list[tuple[str, str]] = [
    ("I used to hate facial hair…",          "but then it grew on me. 🧔"),
    ("Why did the bicycle fall over?",       "Because it was two-tired! 🚲"),
    ("What time did the man go to the dentist?", "Tooth-hurty! 🦷"),
    ("I'm on a seafood diet.",               "I see food and I eat it. 🍔"),
    ("What do you call a sleeping dinosaur?", "A dino-snore! 🦕"),
]

_DARK_JOKES: list[str] = [
    "I told a joke about paper. It was tearable. 📄",
    "My wife told me I had to stop acting like a flamingo. I had to put my foot down. 🦩",
    "I asked my dog what two minus two is. He said nothing. 🐕",
    "Why don't graveyards ever get overcrowded? Because people are dying to get in. ⚰️",
]

_MAGIC_8_RESPONSES: list[str] = [
    "🎱 **It is certain.**",        "🎱 **It is decidedly so.**",
    "🎱 **Without a doubt.**",      "🎱 **Yes, definitely.**",
    "🎱 **You may rely on it.**",   "🎱 **As I see it, yes.**",
    "🎱 **Most likely.**",          "🎱 **Outlook good.**",
    "🎱 **Yes.**",                  "🎱 **Signs point to yes.**",
    "🎱 **Reply hazy, try again.**","🎱 **Ask again later.**",
    "🎱 **Better not tell you now.**","🎱 **Cannot predict now.**",
    "🎱 **Concentrate and ask again.**","🎱 **Don't count on it.**",
    "🎱 **My reply is no.**",       "🎱 **My sources say no.**",
    "🎱 **Outlook not so good.**",  "🎱 **Very doubtful.**",
]

_ROASTS: list[str] = [
    "You're like a cloud ☁️ — when you disappear, it's a beautiful day.",
    "I'd roast you, but my mom said I'm not allowed to burn trash. 🗑️",
    "You have your entire life to be an idiot. Why not take today off? 😴",
    "I'm not saying you're dumb, but you'd have to study hard to become an idiot. 📚",
    "You're the reason they put instructions on shampoo bottles. 🧴",
    "I'd explain it to you, but I don't have any crayons with me. 🖍️",
    "You're like a software update. Whenever I see you, I think 'Not now.' 💻",
    "I was going to tell you a joke about your life… but I see it's already one. 😂",
]

_MEME_URLS: list[str] = [
    "https://i.imgflip.com/4t0m5.jpg",    # Drake
    "https://i.imgflip.com/1bij.jpg",     # One does not simply
    "https://i.imgflip.com/1otk96.jpg",   # Two buttons
    "https://i.imgflip.com/9ehk.jpg",     # Distracted boyfriend
    "https://i.imgflip.com/1g8my4.jpg",   # Mocking SpongeBob
    "https://i.imgflip.com/2hgfw.jpg",    # Change my mind
]

_TRIVIA: list[dict] = [
    {"q": "What planet is closest to the Sun?",         "a": "mercury", "hint": "Tiny and rocky 🪨"},
    {"q": "How many continents are there on Earth?",    "a": "7",       "hint": "More than 6, less than 8 🌍"},
    {"q": "What is the capital of France?",             "a": "paris",   "hint": "City of Lights 🗼"},
    {"q": "Who painted the Mona Lisa?",                 "a": "da vinci","hint": "Italian Renaissance genius 🎨"},
    {"q": "What is the chemical symbol for gold?",      "a": "au",      "hint": "From the Latin 'Aurum' ✨"},
    {"q": "How many sides does a hexagon have?",        "a": "6",       "hint": "Like a honeycomb 🐝"},
    {"q": "What is the largest ocean on Earth?",        "a": "pacific", "hint": "Its name means peaceful 🌊"},
    {"q": "In what year did World War II end?",         "a": "1945",    "hint": "Mid-1940s 📅"},
    {"q": "What is the fastest land animal?",           "a": "cheetah", "hint": "Big spotted cat 🐆"},
    {"q": "How many bones are in the adult human body?","a": "206",     "hint": "Between 200 and 210 🦴"},
]

_TRUTHS: list[str] = [
    "What's the most embarrassing thing you've ever done? 😳",
    "What's a secret you've never told anyone in this server? 🤫",
    "Who was your first crush? 💘",
    "What's the worst lie you've ever told? 🤥",
    "What's your biggest fear? 😨",
    "Have you ever cheated on a test? 📝",
    "What's the most childish thing you still do? 🧸",
    "What's your most embarrassing username from the past? 💻",
]

_DARES: list[str] = [
    "Send the last photo in your camera roll! 📸",
    "Type your next message with your nose! 👃",
    "Say something nice about everyone currently online in this server! 💬",
    "Change your nickname to 'PotatoHead' for 10 minutes! 🥔",
    "Send a voice message of you singing for 10 seconds! 🎤",
    "Write a poem about the last person who messaged in this chat! 📜",
    "Type your next 3 messages using only emojis! 🎭",
    "Share your most embarrassing autocorrect fail! 📱",
]


# ── Active game states ─────────────────────────────────────────────────────────
# Structure: { channel_id: { user_id: { "type": str, ...extra state } } }
game_states: dict[str, dict[str, dict]] = {}


# ── Joke functions ─────────────────────────────────────────────────────────────

def tell_joke(joke_type: str = "random") -> str:
    """Return a formatted joke string. Punchlines are Discord spoiler-tagged."""
    t = joke_type.lower()
    if "dad" in t:
        setup, punchline = random.choice(_DAD_JOKES)
        return f"👨 **Dad Joke Time!**\n\n*{setup}*\n\n||{punchline}||"
    if "dark" in t:
        return f"😈 **Dark Humor Warning:**\n\n||{random.choice(_DARK_JOKES)}||"
    setup, punchline = random.choice(_JOKES)
    return f"😂 **Here's a joke!**\n\n*{setup}*\n\n||{punchline}||"


# ── Magic 8-Ball ───────────────────────────────────────────────────────────────

def magic_8ball(question: str = "") -> str:
    """Return a Magic 8-Ball response, optionally echoing the question."""
    response = random.choice(_MAGIC_8_RESPONSES)
    if question:
        return f"🎱 **Question:** {question}\n\n{response}"
    return response


# ── Roast ──────────────────────────────────────────────────────────────────────

def roast(target: str = "you") -> str:
    """Return a random roast aimed at *target*."""
    return f"🔥 **Roast for {target}:**\n\n{random.choice(_ROASTS)}"


# ── Meme ───────────────────────────────────────────────────────────────────────

def get_meme() -> str:
    """Return a random meme image URL."""
    return f"😂 **Random Meme!**\n{random.choice(_MEME_URLS)}"


# ── Mini-games ─────────────────────────────────────────────────────────────────

def start_game(game_type: str, channel_id: str, user_id: str) -> str:
    """
    Initialise a mini-game for (*channel_id*, *user_id*) and return the
    opening message shown to the player.

    Supported *game_type* values: ``rps``, ``number_guess``, ``trivia``,
    ``truth_or_dare`` (or ``truth``, ``dare``).  Any other value picks randomly.
    """
    t = game_type.lower()

    if "rock" in t or "rps" in t or "paper" in t or "scissors" in t:
        game_states.setdefault(channel_id, {})[user_id] = {"type": "rps"}
        return (
            "✊✋✌️ **Rock, Paper, Scissors!**\n\n"
            "Reply with: `rock`, `paper`, or `scissors`"
        )

    if "number" in t or "guess" in t:
        number = random.randint(1, 100)
        game_states.setdefault(channel_id, {})[user_id] = {
            "type": "number_guess", "number": number, "attempts": 0,
        }
        return (
            "🔢 **Number Guessing Game!**\n\n"
            "I'm thinking of a number between **1 and 100**.\n"
            "Type your guess!"
        )

    if "trivia" in t:
        q = random.choice(_TRIVIA)
        game_states.setdefault(channel_id, {})[user_id] = {
            "type": "trivia", "answer": q["a"], "hint": q["hint"],
        }
        return (
            f"🎯 **Trivia Time!**\n\n"
            f"**Q:** {q['q']}\n\n"
            "*(Type your answer or say `hint`)*"
        )

    if "truth" in t or "dare" in t:
        truth = random.choice(_TRUTHS)
        dare  = random.choice(_DARES)
        return (
            "🎭 **Truth or Dare?**\n\n"
            f"**TRUTH:** {truth}\n\n"
            f"**DARE:** {dare}\n\n"
            "*Choose your fate!*"
        )

    # Unknown type → pick randomly
    return start_game(random.choice(["rps", "number_guess", "trivia", "truth_or_dare"]),
                      channel_id, user_id)


def process_game_input(user_input: str, channel_id: str, user_id: str) -> str | None:
    """
    Handle the player's reply to an active mini-game.

    Returns the bot's response string, or ``None`` if there is no active
    game or the input is not a valid game move.
    """
    state = game_states.get(channel_id, {}).get(user_id)
    if not state:
        return None

    game_type = state["type"]

    # ── Rock Paper Scissors ──────────────────────────────────────────────────
    if game_type == "rps":
        choices   = {"rock", "paper", "scissors"}
        user_pick = user_input.lower().strip()
        if user_pick not in choices:
            return None
        bot_pick = random.choice(list(choices))
        emoji    = {"rock": "✊", "paper": "✋", "scissors": "✌️"}

        wins_against = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        if user_pick == bot_pick:
            result = "🤝 **It's a tie!**"
        elif wins_against[user_pick] == bot_pick:
            result = "🎉 **You win!**"
        else:
            result = "😈 **I win!**"

        del game_states[channel_id][user_id]
        return (
            f"{emoji[user_pick]} You chose **{user_pick}**\n"
            f"{emoji[bot_pick]} I chose **{bot_pick}**\n\n"
            f"{result}"
        )

    # ── Number Guess ────────────────────────────────────────────────────────
    if game_type == "number_guess":
        try:
            guess = int(user_input.strip())
        except ValueError:
            return None
        state["attempts"] += 1
        number = state["number"]
        if guess == number:
            attempts = state["attempts"]
            del game_states[channel_id][user_id]
            praise = "🏆 Amazing!" if attempts <= 5 else "Good job!"
            return (
                f"🎉 **CORRECT!** The number was **{number}**!\n"
                f"You got it in **{attempts} attempt(s)**! {praise}"
            )
        hint = "📈 **Too low!** Try higher." if guess < number else "📉 **Too high!** Try lower."
        return f"{hint} *(Attempt {state['attempts']})*"

    # ── Trivia ───────────────────────────────────────────────────────────────
    if game_type == "trivia":
        user_ans = user_input.lower().strip()
        if user_ans == "hint":
            return f"💡 **Hint:** {state['hint']}"
        correct = state["answer"].lower()
        if user_ans == correct or correct in user_ans:
            del game_states[channel_id][user_id]
            return f"✅ **Correct!** 🎉 The answer was **{state['answer']}**!"
        return "❌ **Wrong!** Try again or type `hint` for a clue."

    return None