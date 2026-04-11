# MTG Commander Deck Crafter — Feature Roadmap

## Phase 1 — Foundation [COMPLETE]
- [x] Scryfall API tool (card lookup, search, rulings, prices, legality)
- [x] Local response caching for Scryfall
- [x] Claude agent with streaming + adaptive thinking + agentic tool use loop
- [x] Commander theory knowledge base (ratios, archetypes, staples)
- [x] Rich terminal CLI with streamed responses and tool call indicators

---

## Phase 2 — Intelligence [COMPLETE]

### EDHREC Integration
- [x] Commander page JSON endpoint integration
- [x] Card popularity data by commander (inclusion %, synergy score)
- [x] Archetype-specific staple recommendations (theme pages)
- [x] Available themes/tribes per commander

### Commander Spellbook Integration
- [x] Combo detection API integration (`/variants/` endpoint)
- [x] Auto-detect combos in any decklist (`find_deck_combos`)
- [x] Suggest missing combo pieces for a deck (`suggest_combo_pieces`)
- [x] Find combos for a specific card or commander

### Deck Analyzer
- [x] Mana curve visualization (CMC distribution by bucket)
- [x] Land count and color pip distribution
- [x] Category ratio checker (ramp, draw, removal, wipes, tutors, counterspells)
- [x] Average CMC scoring with assessment
- [x] Actionable recommendations vs. Commander targets

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
| 2 | **Commander Spellbook API** | Combo database | DONE |
| 3 | **EDHREC** | Popularity data, commander recommendations | DONE |
| 4 | **MTGJson** | Bulk offline card data | Phase 2 |
| 5 | **Moxfield** | Import/export, popular decklists | Phase 3 |
| 6 | **TCGPlayer API** | Detailed pricing | Phase 3 |
| 7 | **ChromaDB** | Semantic card search ("cards like X") | Phase 4 |
| 8 | **Archidekt** | Alternative deck import/export | Phase 3 |
