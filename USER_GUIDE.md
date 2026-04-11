# MTG Commander Deck Crafter — User Guide

## What is this?

An AI-powered deck building assistant for Magic: The Gathering's Commander (EDH) format. You chat with it in your terminal, and it uses Claude's AI reasoning plus live card data from Scryfall to help you build, refine, and understand Commander decks.

---

## Setup

**Requirements:** Python 3.14+, an Anthropic API key

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Add your API key**
```bash
cp .env.example .env
```
Then open `.env` and replace `your_anthropic_api_key_here` with your key from [console.anthropic.com](https://console.anthropic.com).

**3. Run it**
```bash
python main.py
```

---

## The Interface

When you start the app you'll see a terminal chat window. Type your message at the `You:` prompt and press Enter.

While the agent thinks, you'll see indicators showing what it's doing in real time — for example:
```
  🔍 Looking up card: Sol Ring
  🃏 Finding cards for commander: Yuriko, the Tiger's Shadow
```
This means it's fetching live data from Scryfall to inform its answer.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/help` | Show available commands and example prompts |
| `/new`  | Clear the conversation and start fresh |
| `/quit` | Exit the program |

You can also exit with `Ctrl+C` at any time.

---

## What You Can Ask

The assistant understands natural language — you don't need special syntax. Here are the types of things it's good at:

### Build a deck from scratch
```
Build me a Yuriko, the Tiger's Shadow ninja deck under $200
Build an Atraxa superfriends deck focused on planeswalkers
I want a fast aggro deck with Isshin, Two Heavens as One
```

### Get card recommendations by role
```
What's the best ramp for a Ur-Dragon deck?
Find me draw engines for my Korvold, Fae-Cursed King deck
What counterspells should I run in a Simic deck?
What are good board wipes for Grixis colors?
```

### Look up specific cards
```
What does Rhystic Study do?
How much does The One Ring cost?
Is Jeweled Lotus legal in Commander?
What are the rulings for Ghostly Prison?
```

### Synergy and strategy advice
```
Find me cards that synergize with Korvold's sacrifice triggers
What tribal support exists for a Merfolk deck?
What are the best ways to abuse Purphoros, God of the Forge?
```

### Analyze a decklist
Paste a list of card names and ask for feedback:
```
Analyze this deck and tell me what's missing:
1 Yuriko, the Tiger's Shadow
1 Arcane Adaptation
1 Brainstorm
... (continue your list)
```

### Budget and pricing
```
What's the price of the top 10 staples for a green ramp deck?
I have a $100 budget — what's the best value commander for it?
```

---

## How It Works

- **Conversation memory:** The assistant remembers everything you've said in the current session. You can refine requests iteratively — e.g., "actually make it more focused on tokens" — and it will build on the previous answer.
- **Live card data:** Card lookups, prices, and searches pull from Scryfall in real time, so information is always current.
- **Color identity enforcement:** When searching for cards for a commander, it automatically filters to cards legal in that commander's color identity.
- **EDHREC popularity:** Search results are ranked by EDHREC popularity by default, so the most-played cards surface first.
- **Local caching:** Individual card lookups are cached locally in `data/cache/` so repeated lookups are instant and don't hit Scryfall again.

### Start a new conversation with `/new`

The agent remembers the full conversation in memory. If you've been building one deck and want to start on a different one, use `/new` to clear the history. This prevents the previous context from influencing the new deck.

---

## Tips for Better Results

**Be specific about your goals.** Instead of "build me a deck", try "build me a combo-focused Thassa's Oracle deck that wins via consultation, under $300".

**Name your commander upfront.** The agent uses the commander to determine legal colors and tailor recommendations.

**State your budget.** Without a budget, suggestions may include expensive staples. Even a rough range ("under $150", "no card over $10") helps significantly.

**Ask follow-up questions.** The conversation is stateful — you can drill in:
- "Now find me budget replacements for the expensive cards"
- "Swap out the counterspells for more removal"
- "Which of those draw engines is the most budget-friendly?"

**Paste real decklists.** If you have an existing deck (from Moxfield, Archidekt, etc.), paste the card names and ask for an analysis or upgrade suggestions.

---

## Limitations (Phase 1)

- No EDHREC integration yet — synergy data comes from card text analysis, not community meta data
- No combo detection — it won't proactively flag two-card win conditions in your list
- No import/export — you'll need to manually copy the suggested lists
- Prices are from Scryfall (TCGPlayer market price) and may not match your local store
