# MTG Commander Deck Crafter

## Project Overview
AI-powered Magic: The Gathering Commander (EDH) deck building assistant. Uses Claude API with tool use and Scryfall for real-time card data.

## Tech Stack
- **Language:** Python 3.14
- **AI:** Claude API (Anthropic) with tool use + adaptive thinking
- **Card Data:** Scryfall API (free, no auth)
- **UI:** Rich terminal CLI (Streamlit planned for Phase 3)

## Project Structure
- `main.py` — Entry point
- `config.py` — API keys, constants
- `agent/agent.py` — Claude agent with streaming + agentic tool use loop; multi-dispatcher routing
- `agent/tools/scryfall.py` — 6 Scryfall tools + dispatcher + local cache
- `agent/tools/deck_analyzer.py` — Mana curve, land count, category ratios, CMC analysis
- `agent/tools/edhrec.py` — EDHREC recommendations, themes, card popularity by commander
- `agent/tools/spellbook.py` — Commander Spellbook combo detection and missing-piece suggestions
- `knowledge/system_prompt.md` — Commander theory, ratios, archetypes, staples
- `ui/cli.py` — Rich terminal chat interface with tool call indicators for all tools
- `data/cache/` — Auto-populated Scryfall response cache
- `Makefile` — Common dev commands
- `USER_GUIDE.md` — End-user documentation

## Build Phases
- **Phase 1 (COMPLETE):** Scryfall tools, Claude agent loop, system prompt, CLI
- **Phase 2 (COMPLETE):** EDHREC integration, Commander Spellbook combos, deck analyzer
- **Phase 3 (NEXT):** Budget engine, import/export, Streamlit web UI
- **Phase 4:** Semantic card search (ChromaDB), Deck Doctor, meta awareness

## How to Run
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY`
3. `python main.py`

## Key Decisions
- Model: `claude-opus-4-6` (configurable in config.py)
- Scryfall rate limit: 100ms delay between requests per their guidelines
- Card responses cached locally in `data/cache/` as JSON
- Agent uses streaming with adaptive thinking for best UX
