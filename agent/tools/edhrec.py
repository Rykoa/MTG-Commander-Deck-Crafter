"""
EDHREC integration — commander card recommendations, synergy scores, and themes.
Uses EDHREC's unofficial JSON endpoints (Next.js static data files).
No authentication required. Cache aggressively — files update at most daily.
"""

import re
import time
import json
import os
import unicodedata
import requests

EDHREC_BASE = "https://edhrec.com"
RATE_LIMIT_DELAY = 0.3  # 300ms between requests per community guidelines
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache", "edhrec"
)
os.makedirs(CACHE_DIR, exist_ok=True)

_last_request_time = 0.0

HEADERS = {
    "User-Agent": "MTG-Commander-Deck-Crafter/1.0 (personal deckbuilding tool)",
    "Accept": "application/json",
    "Referer": "https://edhrec.com/",
}


# ─── Slug + HTTP helpers ──────────────────────────────────────────────────────

def _commander_slug(name: str) -> str:
    """Convert a commander name to an EDHREC URL slug."""
    # Normalize unicode (é → e, ü → u, etc.)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    # Strip punctuation that isn't hyphens or spaces
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    # Spaces to hyphens, collapse multiples
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"-+", "-", name)
    return name


def _cache_path(slug: str, suffix: str = "") -> str:
    key = f"{slug}{suffix}"
    return os.path.join(CACHE_DIR, f"{key}.json")


def _get_json(url: str, cache_key: str) -> dict | None:
    """Fetch a URL with caching. Returns None on error."""
    global _last_request_time

    path = _cache_path(cache_key)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)

    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        _last_request_time = time.time()
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        with open(path, "w") as f:
            json.dump(data, f)
        return data
    except Exception:
        return None


def _get_commander_raw(slug: str) -> dict | None:
    url = f"{EDHREC_BASE}/commanders/{slug}.json"
    return _get_json(url, slug)


# ─── Parsing helpers ──────────────────────────────────────────────────────────

def _extract_cardlists(data: dict) -> list[dict]:
    return (
        data.get("container", {})
        .get("json_dict", {})
        .get("cardlists", [])
    )


def _extract_panels(data: dict) -> dict:
    return (
        data.get("container", {})
        .get("json_dict", {})
        .get("panels", {})
    )


def _extract_commander_meta(data: dict) -> dict:
    return (
        data.get("container", {})
        .get("json_dict", {})
        .get("card", {})
    )


def _format_card_entry(card: dict, section_tag: str) -> dict:
    prices = card.get("prices", {}) or {}
    return {
        "name": card.get("name", ""),
        "inclusion_pct": card.get("inclusion", 0),
        "synergy": round(card.get("synergy", 0.0), 3),
        "section": section_tag,
        "cmc": card.get("cmc"),
        "primary_type": card.get("primary_type", ""),
        "price_usd": prices.get("tcgplayer"),
    }


# ─── Tool functions ───────────────────────────────────────────────────────────

def get_commander_recommendations(
    commander_name: str,
    min_inclusion: int = 10,
    max_results: int = 30,
) -> dict:
    """
    Get EDHREC's top recommended cards for a commander.

    Returns cards sorted by inclusion percentage, with synergy scores.
    Synergy > 0 means the card appears more with this commander than average.
    Synergy < 0 means it's a generic staple used across many decks.

    Args:
        commander_name: The commander's card name.
        min_inclusion: Minimum % of decks that include this card (default 10).
        max_results: Max cards to return per call (default 30).
    """
    slug = _commander_slug(commander_name)
    data = _get_commander_raw(slug)

    if data is None:
        return {
            "error": f"Commander '{commander_name}' not found on EDHREC. "
                     f"Check the name or try a different spelling."
        }

    meta = _extract_commander_meta(data)
    cardlists = _extract_cardlists(data)

    all_cards = []
    for section in cardlists:
        tag = section.get("tag", "")
        for card in section.get("cardviews", []):
            if card.get("inclusion", 0) >= min_inclusion:
                all_cards.append(_format_card_entry(card, tag))

    all_cards.sort(key=lambda c: c["inclusion_pct"], reverse=True)

    return {
        "commander": meta.get("name", commander_name),
        "total_decks_on_edhrec": meta.get("num_decks", 0),
        "color_identity": meta.get("color_identity", []),
        "card_count": len(all_cards),
        "cards": all_cards[:max_results],
    }


def get_commander_themes(commander_name: str) -> dict:
    """
    Get the available themes and archetypes for a commander from EDHREC.
    Each theme represents a focused build direction with its own card list.

    Args:
        commander_name: The commander's card name.
    """
    slug = _commander_slug(commander_name)
    data = _get_commander_raw(slug)

    if data is None:
        return {
            "error": f"Commander '{commander_name}' not found on EDHREC."
        }

    panels = _extract_panels(data)
    themes = panels.get("themes", [])
    tribes = panels.get("tribes", [])

    return {
        "commander": commander_name,
        "themes": [
            {"name": t.get("name", ""), "deck_count": t.get("count", 0)}
            for t in themes
        ],
        "tribes": [
            {"name": t.get("name", ""), "deck_count": t.get("count", 0)}
            for t in tribes
        ],
    }


def get_theme_recommendations(
    commander_name: str,
    theme: str,
    min_inclusion: int = 5,
    max_results: int = 30,
) -> dict:
    """
    Get EDHREC card recommendations for a specific theme/archetype build
    of a commander (e.g. Niv-Mizzet + "wheels" theme).

    Args:
        commander_name: The commander's card name.
        theme: Theme name (e.g. "wheels", "spellslinger", "dragons").
               Use get_commander_themes first to see available themes.
        min_inclusion: Minimum inclusion % filter (default 5).
        max_results: Max cards to return (default 30).
    """
    slug = _commander_slug(commander_name)
    theme_slug = _commander_slug(theme)
    cache_key = f"{slug}_{theme_slug}"
    url = f"{EDHREC_BASE}/commanders/{slug}/{theme_slug}.json"

    data = _get_json(url, cache_key)

    if data is None:
        return {
            "error": f"Theme '{theme}' not found for commander '{commander_name}'. "
                     f"Use get_commander_themes to see available themes."
        }

    cardlists = _extract_cardlists(data)

    all_cards = []
    for section in cardlists:
        tag = section.get("tag", "")
        for card in section.get("cardviews", []):
            if card.get("inclusion", 0) >= min_inclusion:
                all_cards.append(_format_card_entry(card, tag))

    all_cards.sort(key=lambda c: c["inclusion_pct"], reverse=True)

    return {
        "commander": commander_name,
        "theme": theme,
        "card_count": len(all_cards),
        "cards": all_cards[:max_results],
    }


# ─── Tool definitions for Claude ─────────────────────────────────────────────

EDHREC_TOOL_DEFINITIONS = [
    {
        "name": "get_commander_recommendations",
        "description": (
            "Get EDHREC's top recommended cards for a commander, ranked by how often "
            "they appear in real decks (inclusion %) and synergy score. "
            "Synergy > 0 means the card is especially popular with this commander. "
            "Synergy < 0 means it's a generic staple. "
            "Use this when the user asks 'what should I put in my X deck?' or wants "
            "community-vetted card suggestions for a specific commander."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commander_name": {
                    "type": "string",
                    "description": "The commander's full card name."
                },
                "min_inclusion": {
                    "type": "integer",
                    "description": "Minimum inclusion percentage filter (0-100). Default 10.",
                    "default": 10
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of cards to return. Default 30.",
                    "default": 30
                }
            },
            "required": ["commander_name"]
        }
    },
    {
        "name": "get_commander_themes",
        "description": (
            "Get the available theme and tribe build directions for a commander from EDHREC. "
            "Themes represent focused archetypes (e.g. 'wheels', 'spellslinger', 'dragons'). "
            "Use this when the user wants to explore different build approaches for a commander, "
            "or before calling get_theme_recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commander_name": {
                    "type": "string",
                    "description": "The commander's full card name."
                }
            },
            "required": ["commander_name"]
        }
    },
    {
        "name": "get_theme_recommendations",
        "description": (
            "Get EDHREC card recommendations for a specific themed build of a commander "
            "(e.g. Niv-Mizzet with a 'wheels' focus). Returns cards ranked by inclusion % "
            "within that theme. Call get_commander_themes first to see valid theme names. "
            "Use this when building a focused archetype deck or when the user specifies "
            "a particular strategy they want to build around."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commander_name": {
                    "type": "string",
                    "description": "The commander's full card name."
                },
                "theme": {
                    "type": "string",
                    "description": "Theme name, e.g. 'wheels', 'spellslinger', 'dragons'. Use get_commander_themes to see options."
                },
                "min_inclusion": {
                    "type": "integer",
                    "description": "Minimum inclusion percentage filter. Default 5.",
                    "default": 5
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of cards to return. Default 30.",
                    "default": 30
                }
            },
            "required": ["commander_name", "theme"]
        }
    },
]


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    tool_map = {
        "get_commander_recommendations": lambda i: get_commander_recommendations(
            i["commander_name"],
            i.get("min_inclusion", 10),
            i.get("max_results", 30),
        ),
        "get_commander_themes": lambda i: get_commander_themes(i["commander_name"]),
        "get_theme_recommendations": lambda i: get_theme_recommendations(
            i["commander_name"],
            i["theme"],
            i.get("min_inclusion", 5),
            i.get("max_results", 30),
        ),
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name](tool_input)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
