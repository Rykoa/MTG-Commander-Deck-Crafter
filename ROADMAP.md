# MTG Commander Deck Crafter — Feature Roadmap

## Phase 1 — Foundation [COMPLETE]
- [x] Scryfall API tool (card lookup, search, rulings, prices, legality)
- [x] Local response caching for Scryfall
- [x] Claude agent with streaming + adaptive thinking + agentic tool use loop
- [x] Commander theory knowledge base (ratios, archetypes, staples)
- [x] Rich terminal CLI with streamed responses and tool call indicators

---

## Phase 2 — Intelligence [NEXT]

### EDHREC Integration
- [ ] Scrape/parse EDHREC commander pages for top cards, synergies, and average decklists
- [ ] Card popularity data by commander
- [ ] Archetype-specific staple recommendations

### Commander Spellbook Integration
- [ ] Combo detection API integration
- [ ] Auto-detect combos in any decklist
- [ ] Suggest missing combo pieces for a deck
- [ ] Flag infinite loops and win conditions

### Deck Analyzer
- [ ] Mana curve visualization
- [ ] Mana base calculator (land count, color ratios, fixing requirements)
- [ ] Category ratio checker (ramp, draw, removal, interaction, threats, win cons)
- [ ] Average CMC scoring
- [ ] Synergy scoring between cards

---

## Phase 3 — Polish

### Budget Engine
- [ ] Real-time price totals for full decklists
- [ ] Budget cap enforcement during building
- [ ] Budget upgrade path suggestions ("Replace X with Y for $10 more")
- [ ] Cheap alternative suggestions for expensive staples

### Import/Export
- [ ] Import from plain text, Moxfield, Archidekt, MTGO format
- [ ] Export to Moxfield/Archidekt import format
- [ ] Save/load decks locally as JSON

### Web UI (Streamlit)
- [ ] Chat interface with conversation history
- [ ] Deck display as formatted card list with prices
- [ ] Copy-to-clipboard for deck export
- [ ] Mana curve chart

---

## Phase 4 — Power Features

### Semantic Card Search
- [ ] ChromaDB vector database for card embeddings
- [ ] "Find me cards like Rhystic Study" (semantic similarity)
- [ ] Role-based suggestions ("Give me more ramp options")

### Deck Doctor
- [ ] Paste an existing deck -> AI identifies weaknesses
- [ ] Suggest targeted improvements by category
- [ ] "Too slow / too few answers / weak mana base" diagnosis
- [ ] Power level assessment (1-10 scale, cEDH-aware)

### Meta Awareness
- [ ] EDHREC "top cards" context by commander
- [ ] Staples awareness by color/archetype
- [ ] cEDH vs casual distinction
- [ ] Pod read ("what does this deck struggle against?")

### Card Recommender
- [ ] Role-based suggestions
- [ ] "What's the best removal for this meta?"
- [ ] Budget-aware alternatives

---

## Integrations (Priority Order)

| Priority | Integration | Purpose | Status |
|---|---|---|---|
| 1 | **Scryfall API** | Card data, search, prices, legality | DONE |
| 2 | **Commander Spellbook API** | Combo database | Phase 2 |
| 3 | **EDHREC** | Popularity data, commander recommendations | Phase 2 |
| 4 | **MTGJson** | Bulk offline card data | Phase 2 |
| 5 | **Moxfield** | Import/export, popular decklists | Phase 3 |
| 6 | **TCGPlayer API** | Detailed pricing | Phase 3 |
| 7 | **ChromaDB** | Semantic card search ("cards like X") | Phase 4 |
| 8 | **Archidekt** | Alternative deck import/export | Phase 3 |
