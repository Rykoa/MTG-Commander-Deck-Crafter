"""
Scryfall API wrapper — provides card lookup, search, and rulings for the MTG agent.
All functions return plain dicts/lists suitable for Claude tool results.
"""

import time
import json
import os
import hashlib
import requests
from config import SCRYFALL_BASE_URL, SCRYFALL_RATE_LIMIT_DELAY, KNOWLEDGE_DIR

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

_last_request_time = 0.0


def _get(endpoint: str, params: dict = None) -> dict:
    """Rate-limited GET request to Scryfall."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < SCRYFALL_RATE_LIMIT_DELAY:
        time.sleep(SCRYFALL_RATE_LIMIT_DELAY - elapsed)

    url = f"{SCRYFALL_BASE_URL}{endpoint}"
    response = requests.get(url, params=params or {}, timeout=10)
    _last_request_time = time.time()

    if response.status_code == 404:
        return {"error": "not_found", "message": "Card or resource not found."}
    if response.status_code == 400:
        data = response.json()
        return {"error": "bad_request", "message": data.get("details", "Bad request.")}
    response.raise_for_status()
    return response.json()


def _post(endpoint: str, payload: dict) -> dict:
    """Rate-limited POST request to Scryfall."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < SCRYFALL_RATE_LIMIT_DELAY:
        time.sleep(SCRYFALL_RATE_LIMIT_DELAY - elapsed)

    url = f"{SCRYFALL_BASE_URL}{endpoint}"
    response = requests.post(url, json=payload, timeout=30)
    _last_request_time = time.time()

    if response.status_code == 404:
        return {"error": "not_found", "message": "Resource not found."}
    if response.status_code == 400:
        data = response.json()
        return {"error": "bad_request", "message": data.get("details", "Bad request.")}
    response.raise_for_status()
    return response.json()


def get_cards_batch(names: list[str]) -> dict[str, dict]:
    """
    Fetch up to 75 cards per request using Scryfall's /cards/collection endpoint.
    Returns a dict mapping lowercased name → formatted card dict.
    Cards already in the local cache are returned without a network call.
    Not-found cards are returned as {"error": "not_found"}.
    """
    result: dict[str, dict] = {}
    to_fetch: list[str] = []

    for name in names:
        cache_path = _cache_key("card", name.lower())
        cached = _read_cache(cache_path)
        if cached:
            result[name.lower()] = cached
        else:
            to_fetch.append(name)

    # Scryfall /cards/collection accepts max 75 identifiers per request
    BATCH_SIZE = 75
    for i in range(0, len(to_fetch), BATCH_SIZE):
        batch = to_fetch[i:i + BATCH_SIZE]
        payload = {"identifiers": [{"name": n} for n in batch]}
        data = _post("/cards/collection", payload)

        if "error" in data:
            for name in batch:
                result[name.lower()] = {"error": "not_found", "name": name}
            continue

        # Map returned cards back by name (lowercased for matching)
        found_names = set()
        for card in data.get("data", []):
            formatted = _format_card(card)
            key = formatted["name"].lower()
            result[key] = formatted
            found_names.add(key)
            cache_path = _cache_key("card", key)
            _write_cache(cache_path, formatted)

        # Mark anything not returned as not found
        for name in batch:
            if name.lower() not in result:
                result[name.lower()] = {"error": "not_found", "name": name}

    return result


def _cache_key(prefix: str, value: str) -> str:
    return os.path.join(CACHE_DIR, f"{prefix}_{hashlib.md5(value.encode()).hexdigest()}.json")


def _read_cache(path: str):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _write_cache(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f)


def _format_card(card: dict) -> dict:
    """Extract the fields most useful for deck-building decisions."""
    if "error" in card:
        return card

    # Handle double-faced cards
    faces = card.get("card_faces", [])
    if faces:
        oracle_text = " // ".join(f.get("oracle_text", "") for f in faces)
        mana_cost = " // ".join(f.get("mana_cost", "") for f in faces)
        type_line = " // ".join(f.get("type_line", "") for f in faces)
    else:
        oracle_text = card.get("oracle_text", "")
        mana_cost = card.get("mana_cost", "")
        type_line = card.get("type_line", "")

    prices = card.get("prices", {})
    usd = prices.get("usd") or prices.get("usd_foil")

    return {
        "name": card.get("name"),
        "mana_cost": mana_cost,
        "cmc": card.get("cmc"),
        "type_line": type_line,
        "oracle_text": oracle_text,
        "color_identity": card.get("color_identity", []),
        "colors": card.get("colors", []),
        "power": card.get("power"),
        "toughness": card.get("toughness"),
        "loyalty": card.get("loyalty"),
        "legalities": {
            "commander": card.get("legalities", {}).get("commander", "unknown")
        },
        "price_usd": usd,
        "scryfall_uri": card.get("scryfall_uri"),
        "edhrec_rank": card.get("edhrec_rank"),
        "keywords": card.get("keywords", []),
    }


# ─── Tool functions (called by the agent) ────────────────────────────────────

def get_card(name: str) -> dict:
    """
    Fetch a single card by name (fuzzy match).
    Returns card details including oracle text, mana cost, color identity, price.
    """
    cache_path = _cache_key("card", name.lower())
    cached = _read_cache(cache_path)
    if cached:
        return cached

    data = _get("/cards/named", {"fuzzy": name})
    result = _format_card(data)
    if "error" not in result:
        _write_cache(cache_path, result)
    return result


def search_cards(query: str, max_results: int = 20) -> dict:
    """
    Search cards using Scryfall syntax.
    Examples:
      - "commander:legal t:creature c:g cmc<=3"
      - "oracle:\"draw a card\" c:u"
      - "t:instant o:counter c:blue"
    Returns a list of matching cards (up to max_results).
    """
    data = _get("/cards/search", {"q": query, "order": "edhrec"})

    if "error" in data:
        return data

    cards = [_format_card(c) for c in data.get("data", [])[:max_results]]
    return {
        "total_cards": data.get("total_cards", 0),
        "returned": len(cards),
        "cards": cards,
    }


def get_cards_for_commander(commander_name: str, category: str = None, max_results: int = 20) -> dict:
    """
    Search for cards legal for a given commander by color identity.
    Optional category filter: 'ramp', 'draw', 'removal', 'wipe', 'tutor', 'counterspell'
    """
    # First get the commander to find its color identity
    commander = get_card(commander_name)
    if "error" in commander:
        return commander

    identity = commander.get("color_identity", [])
    if not identity:
        color_query = "c:colorless"
    else:
        color_query = f"id<={''.join(identity)}"

    category_queries = {
        "ramp": f"({color_query}) (o:\"add\" o:\"mana\" OR t:\"mana\" OR o:\"land\" t:permanent) game:paper f:commander",
        "draw": f"({color_query}) o:\"draw\" game:paper f:commander",
        "removal": f"({color_query}) (o:\"destroy\" OR o:\"exile\" OR o:\"sacrifice\") game:paper f:commander",
        "wipe": f"({color_query}) (o:\"destroy all\" OR o:\"exile all\" OR o:\"each creature\") game:paper f:commander",
        "tutor": f"({color_query}) o:\"search your library\" game:paper f:commander",
        "counterspell": f"({color_query}) o:\"counter target\" game:paper f:commander",
    }

    if category and category.lower() in category_queries:
        query = category_queries[category.lower()]
    else:
        query = f"({color_query}) game:paper f:commander"

    result = search_cards(query, max_results)
    result["commander"] = commander_name
    result["color_identity"] = identity
    result["category"] = category
    return result


def get_card_rulings(name: str) -> dict:
    """Fetch official rulings for a card by name."""
    card = _get("/cards/named", {"fuzzy": name})
    if "error" in card:
        return card

    rulings_data = _get(f"/cards/{card['id']}/rulings")
    if "error" in rulings_data:
        return rulings_data

    return {
        "card": card.get("name"),
        "rulings": [
            {"date": r["published_at"], "text": r["comment"]}
            for r in rulings_data.get("data", [])
        ],
    }


def get_card_prices(names: list) -> dict:
    """
    Fetch current prices for a list of card names.
    Returns name → USD price mapping.
    """
    results = {}
    for name in names:
        card = get_card(name)
        results[name] = card.get("price_usd", "unknown") if "error" not in card else "not found"
    return {"prices": results}


def check_commander_legality(card_name: str) -> dict:
    """Check whether a card is legal in Commander format."""
    card = get_card(card_name)
    if "error" in card:
        return card
    legality = card.get("legalities", {}).get("commander", "unknown")
    return {
        "card": card_name,
        "commander_legal": legality == "legal",
        "status": legality,
    }


# ─── Tool definitions for Claude ─────────────────────────────────────────────

SCRYFALL_TOOL_DEFINITIONS = [
    {
        "name": "get_card",
        "description": (
            "Look up a single Magic: The Gathering card by name. "
            "Returns oracle text, mana cost, color identity, CMC, type, price, and EDHREC rank. "
            "Use this to get details on a specific card you want to evaluate or recommend."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The card name. Fuzzy matching is supported (e.g., 'Sol Ring', 'rhystic study')."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "search_cards",
        "description": (
            "Search Magic: The Gathering cards using Scryfall syntax. "
            "Use this to find cards matching specific criteria. "
            "Results are ordered by EDHREC popularity. "
            "Example queries: "
            "'t:creature c:g cmc<=2 f:commander' (green creatures CMC 2 or less), "
            "'o:\"draw a card\" c:u f:commander' (blue cards that draw), "
            "'t:instant o:\"counter target\" f:commander' (counterspells). "
            "Always include 'f:commander' to filter to Commander-legal cards."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Scryfall search syntax query string."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of cards to return. Default 20, max 30.",
                    "default": 20
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_cards_for_commander",
        "description": (
            "Search for cards that are legal for a specific commander based on color identity. "
            "Optionally filter by role category: ramp, draw, removal, wipe, tutor, counterspell. "
            "Use this when building or filling out a specific part of a deck."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commander_name": {
                    "type": "string",
                    "description": "The name of the commander."
                },
                "category": {
                    "type": "string",
                    "description": "Card role category: ramp, draw, removal, wipe, tutor, counterspell. Omit for general search.",
                    "enum": ["ramp", "draw", "removal", "wipe", "tutor", "counterspell"]
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of cards to return. Default 20.",
                    "default": 20
                }
            },
            "required": ["commander_name"]
        }
    },
    {
        "name": "get_card_rulings",
        "description": "Get the official Wizards of the Coast rulings for a card. Use this to clarify how a card works in edge cases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The card name."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "get_card_prices",
        "description": "Get current TCGPlayer USD prices for a list of cards. Use this to check budget or compare card costs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of card names to price check."
                }
            },
            "required": ["names"]
        }
    },
    {
        "name": "check_commander_legality",
        "description": "Check whether a specific card is legal in Commander format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_name": {
                    "type": "string",
                    "description": "The card name to check."
                }
            },
            "required": ["card_name"]
        }
    },
]


# ─── Dispatcher (maps tool name → function call) ─────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a Scryfall tool call and return the result as a JSON string."""
    tool_map = {
        "get_card": lambda i: get_card(i["name"]),
        "search_cards": lambda i: search_cards(i["query"], i.get("max_results", 20)),
        "get_cards_for_commander": lambda i: get_cards_for_commander(
            i["commander_name"], i.get("category"), i.get("max_results", 20)
        ),
        "get_card_rulings": lambda i: get_card_rulings(i["name"]),
        "get_card_prices": lambda i: get_card_prices(i["names"]),
        "check_commander_legality": lambda i: check_commander_legality(i["card_name"]),
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name](tool_input)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
