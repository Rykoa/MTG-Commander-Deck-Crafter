"""
Deck Analyzer — evaluates a Commander decklist for mana curve, category ratios,
mana base, and gives actionable recommendations.

Input: a list of card names (the 99 + commander).
Cards are looked up via Scryfall to get CMC, type line, and oracle text.
"""

import re
from agent.tools.scryfall import get_cards_batch


# ─── Category detection ───────────────────────────────────────────────────────

# Keywords/phrases in oracle text that indicate a card's role
CATEGORY_PATTERNS = {
    "ramp": [
        r"add \{[WUBRGC]\}",
        r"add one mana",
        r"add two mana",
        r"add mana",
        r"search your library for a? ?(basic )?land",
        r"put.{0,30}land.{0,30}onto the battlefield",
        r"land.{0,20}you control.{0,20}produce",
    ],
    "draw": [
        r"draw (a|two|three|\d+) cards?",
        r"draw cards equal",
        r"draw that many",
        r"look at the top",
        r"scry \d",
    ],
    "removal": [
        r"destroy target",
        r"exile target",
        r"return target.{0,40}to (its owner'?s?|your|their) hand",
        r"deals? \d+ damage to (any target|target creature|target player)",
    ],
    "wipe": [
        r"destroy all",
        r"exile all",
        r"all creatures get -",
        r"each creature deals? damage",
        r"deals? \d+ damage to each",
        r"return all",
    ],
    "tutor": [
        r"search your library",
    ],
    "counterspell": [
        r"counter target",
        r"counter that spell",
    ],
    "token": [
        r"create (a|two|three|an?|\d+).{0,40}tokens?",
    ],
    "graveyard": [
        r"return.{0,40}from (your|a|the) graveyard",
        r"flashback",
        r"unearth",
        r"dredge",
        r"mill",
    ],
}

# Commander-recommended ratios (targets for a 100-card deck)
RECOMMENDED = {
    "ramp":        {"min": 10, "target": 12},
    "draw":        {"min": 10, "target": 12},
    "removal":     {"min": 8,  "target": 10},
    "wipe":        {"min": 3,  "target": 4},
    "tutor":       {"min": 0,  "target": 5},
    "counterspell":{"min": 0,  "target": 5},
    "lands":       {"min": 35, "target": 37},
}

COLOR_SYMBOLS = {"W", "U", "B", "R", "G", "C"}


def _detect_categories(oracle_text: str, type_line: str) -> list[str]:
    """Return a list of category labels that match this card."""
    text = (oracle_text + " " + type_line).lower()
    matched = []
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                matched.append(category)
                break
    return matched


def _extract_pips(mana_cost: str) -> dict[str, int]:
    """Count colored mana pips in a mana cost string like {2}{U}{U}{R}."""
    counts = {c: 0 for c in "WUBRG"}
    for symbol in re.findall(r"\{([^}]+)\}", mana_cost or ""):
        for char in symbol:
            if char in counts:
                counts[char] += 1
    return {k: v for k, v in counts.items() if v > 0}


def _cmc_bucket(cmc: float) -> str:
    cmc = int(cmc or 0)
    if cmc == 0: return "0"
    if cmc == 1: return "1"
    if cmc == 2: return "2"
    if cmc == 3: return "3"
    if cmc == 4: return "4"
    if cmc == 5: return "5"
    return "6+"


# ─── Main tool function ───────────────────────────────────────────────────────

def analyze_deck(card_names: list[str]) -> dict:
    """
    Analyze a Commander decklist.

    Looks up each card via Scryfall, then computes:
    - Mana curve (CMC distribution)
    - Average CMC (non-land)
    - Land count
    - Category counts (ramp, draw, removal, etc.)
    - Color pip distribution
    - Actionable recommendations

    Args:
        card_names: List of card names in the deck (include the commander).

    Returns:
        Analysis dict with curve, categories, lands, avg_cmc, recommendations.
    """
    if not card_names:
        return {"error": "No cards provided."}

    def _clean_name(raw: str) -> str | None:
        """
        Parse a single line from an Archidekt (or similar) text export into a
        plain card name, or return None if the line should be skipped.

        Handles:
          - Empty lines and comment lines (// or #)
          - Section headers with no leading quantity: "Commander (1)", "Ramp (12)"
          - Leading quantities: "1 Sol Ring", "1x Sol Ring"
          - Trailing set code + collector number: "Sol Ring (M21) 268"
          - Foil markers: "Sol Ring *F*", "Sol Ring (Foil)"
        """
        raw = raw.strip()
        if not raw:
            return None
        # Skip comment lines
        if raw.startswith("//") or raw.startswith("#"):
            return None
        # Skip section headers: no leading digit, ends with (N)
        # e.g. "Commander (1)", "Ramp (12)", "Card Draw (8)"
        if not re.match(r"^\d", raw) and re.search(r"\(\d+\)\s*$", raw):
            return None
        # Strip leading quantity: "1 " or "1x "
        raw = re.sub(r"^\d+x?\s+", "", raw)
        # Strip trailing set code + optional collector number: "(M21) 268" or "(M21)"
        raw = re.sub(r"\s*\([A-Z0-9]{2,5}\)\s*\d*\s*$", "", raw)
        # Strip foil markers
        raw = re.sub(r"\s*\*[Ff]\*\s*$", "", raw)
        raw = re.sub(r"\s*\(Foil\)\s*$", "", raw, flags=re.IGNORECASE)
        return raw.strip() or None

    cleaned_names = [c for n in card_names if (c := _clean_name(n)) is not None]

    curve = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6+": 0}
    categories = {cat: [] for cat in CATEGORY_PATTERNS}
    land_names = []
    pip_totals = {c: 0 for c in "WUBRG"}
    non_land_cmc_total = 0
    non_land_count = 0
    not_found = []

    # Fetch all cards in bulk (2 requests for a 100-card deck instead of 100)
    card_map = get_cards_batch(cleaned_names)

    for name in cleaned_names:
        card = card_map.get(name.lower(), {"error": "not_found", "name": name})
        if "error" in card:
            not_found.append(name)
            continue

        type_line = card.get("type_line", "")
        oracle_text = card.get("oracle_text", "")
        cmc = card.get("cmc") or 0
        mana_cost = card.get("mana_cost", "") or ""

        is_land = "Land" in type_line

        if is_land:
            land_names.append(card["name"])
        else:
            curve[_cmc_bucket(cmc)] += 1
            non_land_cmc_total += cmc
            non_land_count += 1

            pips = _extract_pips(mana_cost)
            for color, count in pips.items():
                pip_totals[color] += count

        # Detect categories for all cards (lands can ramp)
        matched = _detect_categories(oracle_text, type_line)
        for cat in matched:
            categories[cat].append(card["name"])

    avg_cmc = round(non_land_cmc_total / non_land_count, 2) if non_land_count else 0
    total_cards = len(card_names) - len(not_found)

    # Build recommendations
    recommendations = []
    category_counts = {cat: len(cards) for cat, cards in categories.items()}

    for cat, targets in RECOMMENDED.items():
        if cat == "lands":
            count = len(land_names)
        else:
            count = category_counts.get(cat, 0)

        if count < targets["min"]:
            recommendations.append(
                f"LOW {cat.upper()}: {count} detected, recommend at least {targets['min']} (target {targets['target']})"
            )
        elif count >= targets["target"]:
            recommendations.append(
                f"OK {cat.upper()}: {count} detected (target {targets['target']})"
            )
        else:
            recommendations.append(
                f"BELOW TARGET {cat.upper()}: {count} detected, target is {targets['target']}"
            )

    # CMC assessment
    if avg_cmc <= 2.5:
        cmc_note = "Very fast curve — likely an aggressive or combo deck."
    elif avg_cmc <= 3.2:
        cmc_note = "Efficient curve — good for most strategies."
    elif avg_cmc <= 3.8:
        cmc_note = "Midrange curve — ensure sufficient ramp."
    else:
        cmc_note = "Heavy curve — consider adding more ramp and low-cost interaction."

    # Color pip breakdown (as percentages)
    total_pips = sum(pip_totals.values())
    color_distribution = {}
    if total_pips:
        for color, count in pip_totals.items():
            if count > 0:
                color_distribution[color] = {
                    "pips": count,
                    "percent": round(count / total_pips * 100, 1)
                }

    return {
        "total_cards_analyzed": total_cards,
        "not_found": not_found,
        "lands": {
            "count": len(land_names),
            "examples": land_names[:5],
        },
        "mana_curve": curve,
        "average_cmc": avg_cmc,
        "cmc_assessment": cmc_note,
        "color_distribution": color_distribution,
        "categories": {
            cat: {"count": len(cards), "examples": cards[:5]}
            for cat, cards in categories.items()
        },
        "recommendations": recommendations,
    }


# ─── Tool definitions for Claude ─────────────────────────────────────────────

DECK_ANALYZER_TOOL_DEFINITIONS = [
    {
        "name": "analyze_deck",
        "description": (
            "Analyze a Commander decklist for mana curve, average CMC, land count, "
            "category ratios (ramp, draw, removal, wipes, tutors, counterspells), "
            "color pip distribution, and actionable recommendations. "
            "Use this when the user pastes a decklist, asks to evaluate their deck, "
            "or asks about their mana base, curve, or category balance. "
            "Input is a list of card names (the full 99 + commander, or any subset). "
            "IMPORTANT: This tool fetches all card data internally via Scryfall — do NOT "
            "call get_card or any other tool for individual cards before calling this. "
            "Pass the full card name list directly and let this tool handle all lookups."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "card_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                "List of card name entries from the deck. Accepts raw Archidekt export lines "
                "directly — quantities ('1 Sol Ring'), set codes ('Sol Ring (M21) 268'), "
                "foil markers ('*F*'), and section headers ('Ramp (12)') are all handled "
                "internally. You do not need to pre-clean the lines."
            )
                }
            },
            "required": ["card_names"]
        }
    }
]


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    import json
    if tool_name == "analyze_deck":
        try:
            result = analyze_deck(tool_input["card_names"])
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
