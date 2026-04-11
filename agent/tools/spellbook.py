"""
Commander Spellbook integration — combo detection and lookup.
API: https://backend.commanderspellbook.com/api/v1/variants/
No authentication required.
"""

import time
import json
import requests

SPELLBOOK_BASE_URL = "https://backend.commanderspellbook.com/api/v1"
RATE_LIMIT_DELAY = 0.1  # 100ms between requests

_last_request_time = 0.0

ZONE_LABELS = {
    "H": "Hand",
    "B": "Battlefield",
    "G": "Graveyard",
    "E": "Exile",
    "L": "Library",
    "C": "Command Zone",
}


def _get(endpoint: str, params: dict = None) -> dict:
    """Rate-limited GET to Commander Spellbook."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)

    url = f"{SPELLBOOK_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params or {}, timeout=10)
    except requests.RequestException as e:
        _last_request_time = time.time()
        return {"error": "request_failed", "message": str(e)}

    _last_request_time = time.time()

    if response.status_code == 404:
        return {"error": "not_found", "message": "Resource not found."}
    try:
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        return {
            "error": "http_error",
            "status_code": response.status_code,
            "message": str(e),
        }
    except ValueError as e:
        return {"error": "invalid_json", "message": str(e)}


def _format_combo(variant: dict) -> dict:
    """Flatten a variant into a clean, agent-friendly dict."""
    cards = [
        {
            "name": u["card"]["name"],
            "zone": ", ".join(ZONE_LABELS.get(z, z) for z in u.get("zoneLocations", [])),
            "must_be_commander": u.get("mustBeCommander", False),
        }
        for u in variant.get("uses", [])
    ]

    templates = [
        t["template"]["name"]
        for t in variant.get("requires", [])
    ]

    results = [p["feature"]["name"] for p in variant.get("produces", [])]

    return {
        "id": variant.get("id"),
        "cards": cards,
        "template_requirements": templates,
        "results": results,
        "prerequisites": variant.get("prerequisites", ""),
        "steps": variant.get("steps", ""),
        "color_identity": variant.get("identity", ""),
        "mana_needed": variant.get("manaNeeded", ""),
        "popularity": variant.get("popularity", 0),
        "card_count": variant.get("numberOfCards", len(cards)),
    }


def _search_variants(query: str, limit: int = 100) -> list[dict]:
    """Run a query against /variants/ and return formatted combo list."""
    data = _get("/variants/", {"q": query, "limit": limit})
    if "error" in data:
        return []
    return [_format_combo(v) for v in data.get("results", [])]


# ─── Tool functions ───────────────────────────────────────────────────────────

def find_combos_for_card(card_name: str, limit: int = 20) -> dict:
    """
    Find all combos that include a specific card.
    Returns a list of combos sorted by popularity.
    """
    combos = _search_variants(f'card:"{card_name}"', limit=limit)
    if not combos:
        return {"card": card_name, "combo_count": 0, "combos": []}
    combos.sort(key=lambda c: c["popularity"], reverse=True)
    return {"card": card_name, "combo_count": len(combos), "combos": combos}


def find_combos_for_commander(commander_name: str, limit: int = 20) -> dict:
    """
    Find combos designed around a specific commander (where the commander
    is flagged as the required commander piece).
    """
    combos = _search_variants(f'commander:"{commander_name}"', limit=limit)
    if not combos:
        return {"commander": commander_name, "combo_count": 0, "combos": []}
    combos.sort(key=lambda c: c["popularity"], reverse=True)
    return {"commander": commander_name, "combo_count": len(combos), "combos": combos}


def find_deck_combos(card_names: list[str]) -> dict:
    """
    Given a list of card names in a deck, find all combos where every
    required named card is present in the deck.

    Searches combos for each card individually, then filters to only
    combos where all named pieces are in the deck.
    """
    if not card_names:
        return {"error": "No card names provided."}

    deck_set = {name.strip().lower() for name in card_names}
    found: dict[str, dict] = {}

    for card_name in card_names:
        combos = _search_variants(f'card:"{card_name}"', limit=100)
        for combo in combos:
            if combo["id"] in found:
                continue
            # Check all named cards in this combo exist in the deck
            combo_card_names = {c["name"].lower() for c in combo["cards"]}
            if combo_card_names.issubset(deck_set):
                found[combo["id"]] = combo

    result_list = sorted(found.values(), key=lambda c: c["popularity"], reverse=True)
    return {
        "deck_card_count": len(card_names),
        "combos_found": len(result_list),
        "combos": result_list,
    }


def suggest_combo_pieces(card_names: list[str], max_suggestions: int = 10) -> dict:
    """
    Given a deck, find combos where you're only 1 card away from completing them.
    Returns the missing card(s) and the combo they would complete.
    """
    if not card_names:
        return {"error": "No card names provided."}

    deck_set = {name.strip().lower() for name in card_names}
    near_misses: dict[str, dict] = {}

    for card_name in card_names:
        combos = _search_variants(f'card:"{card_name}"', limit=100)
        for combo in combos:
            if combo["id"] in near_misses:
                continue
            combo_card_names = {c["name"].lower() for c in combo["cards"]}
            missing = combo_card_names - deck_set
            if len(missing) == 1:
                missing_name = next(iter(missing))
                near_misses[combo["id"]] = {
                    **combo,
                    "missing_card": missing_name,
                }

    suggestions = sorted(near_misses.values(), key=lambda c: c["popularity"], reverse=True)
    return {
        "near_complete_combos": len(suggestions),
        "suggestions": suggestions[:max_suggestions],
    }


# ─── Tool definitions for Claude ─────────────────────────────────────────────

SPELLBOOK_TOOL_DEFINITIONS = [
    {
        "name": "find_combos_for_card",
        "description": (
            "Find all Commander Spellbook combos that include a specific card. "
            "Returns combo pieces, steps, prerequisites, and win conditions. "
            "Use when the user asks 'what combos does this card enable?' or wants "
            "to know the combo potential of a card they're considering."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "card_name": {
                    "type": "string",
                    "description": "The exact card name to search combos for."
                },
                "limit": {
                    "type": "integer",
                    "description": "Max combos to return. Default 20.",
                    "default": 20
                }
            },
            "required": ["card_name"]
        }
    },
    {
        "name": "find_combos_for_commander",
        "description": (
            "Find combos from Commander Spellbook where a specific card must be the commander. "
            "Use when building around a commander and wanting to find synergistic infinite combos "
            "or win conditions that leverage the commander specifically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commander_name": {
                    "type": "string",
                    "description": "The commander's full card name."
                },
                "limit": {
                    "type": "integer",
                    "description": "Max combos to return. Default 20.",
                    "default": 20
                }
            },
            "required": ["commander_name"]
        }
    },
    {
        "name": "find_deck_combos",
        "description": (
            "Given a list of cards in a deck, find all combos where every required "
            "named piece is already present in the deck. "
            "Use this to detect existing combo lines in a decklist the user shares, "
            "or to check if a proposed deck has any built-in win conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "card_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All card names in the deck."
                }
            },
            "required": ["card_names"]
        }
    },
    {
        "name": "suggest_combo_pieces",
        "description": (
            "Given a deck, find combos where only 1 named card is missing. "
            "Returns the missing card and the combo it would complete. "
            "Use this to suggest high-impact single additions that enable infinite combos or win conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "card_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All card names in the deck."
                },
                "max_suggestions": {
                    "type": "integer",
                    "description": "Maximum number of combo suggestions to return. Default 10.",
                    "default": 10
                }
            },
            "required": ["card_names"]
        }
    },
]


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "find_combos_for_card": lambda i: find_combos_for_card(
            i["card_name"], i.get("limit", 20)
        ),
        "find_combos_for_commander": lambda i: find_combos_for_commander(
            i["commander_name"], i.get("limit", 20)
        ),
        "find_deck_combos": lambda i: find_deck_combos(i["card_names"]),
        "suggest_combo_pieces": lambda i: suggest_combo_pieces(
            i["card_names"], i.get("max_suggestions", 10)
        ),
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name](tool_input)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
