"""
MTG Commander Deck Crafter — CLI Interface
Rich-formatted terminal chat with the deck building agent.
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.rule import Rule
from rich import print as rprint
from agent.agent import DeckCrafterAgent

console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════╗
║         MTG COMMANDER DECK CRAFTER                      ║
║         Powered by Claude + Scryfall                    ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
[bold cyan]Commands:[/bold cyan]
  [yellow]/new[/yellow]      — Start a new conversation (clear history)
  [yellow]/quit[/yellow]     — Exit the program
  [yellow]/help[/yellow]     — Show this help message

[bold cyan]Example prompts:[/bold cyan]
  • Build me a Yuriko, the Tiger's Shadow ninja deck under $200
  • What's the best ramp for a Ur-Dragon deck?
  • Analyze this deck: [paste decklist]
  • Find me cards that synergize with Korvold, Fae-Cursed King
  • What are the best counterspells for a Simic deck?
"""


def on_tool_use(tool_name: str, tool_input: dict):
    """Display a subtle indicator when the agent calls a tool."""
    input_summary = ""
    if "name" in tool_input:
        input_summary = f"[dim]{tool_input['name']}[/dim]"
    elif "query" in tool_input:
        input_summary = f"[dim]{tool_input['query'][:60]}[/dim]"
    elif "commander_name" in tool_input:
        cat = tool_input.get("category", "")
        input_summary = f"[dim]{tool_input['commander_name']}{' / ' + cat if cat else ''}[/dim]"
    elif "names" in tool_input:
        input_summary = f"[dim]{', '.join(tool_input['names'][:3])}{'...' if len(tool_input['names']) > 3 else ''}[/dim]"
    elif "card_name" in tool_input:
        input_summary = f"[dim]{tool_input['card_name']}[/dim]"

    tool_display = {
        # Scryfall
        "get_card": "🔍 Looking up card",
        "search_cards": "🔎 Searching cards",
        "get_cards_for_commander": "🃏 Finding cards for commander",
        "get_card_rulings": "📜 Fetching rulings",
        "get_card_prices": "💰 Checking prices",
        "check_commander_legality": "✅ Checking legality",
        # Deck Analyzer
        "analyze_deck": "📊 Analyzing deck",
        # Commander Spellbook
        "find_combos_for_card": "♾️  Finding combos for card",
        "find_combos_for_commander": "♾️  Finding commander combos",
        "find_deck_combos": "♾️  Scanning deck for combos",
        "suggest_combo_pieces": "♾️  Suggesting combo completions",
        # EDHREC
        "get_commander_recommendations": "📈 Fetching EDHREC recommendations",
        "get_commander_themes": "🎯 Fetching commander themes",
        "get_theme_recommendations": "🎯 Fetching theme recommendations",
    }
    label = tool_display.get(tool_name, f"🔧 {tool_name}")
    console.print(f"  {label}: {input_summary}", style="dim cyan")


def run():
    console.print(BANNER, style="bold green")
    console.print(
        Panel(
            "[white]Your personal MTG Commander deck building assistant.\n"
            "Type [yellow]/help[/yellow] for commands or just start chatting![/white]",
            border_style="green"
        )
    )

    agent = DeckCrafterAgent()
    streaming_buffer = []

    while True:
        try:
            console.print()
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye! May your draws be legendary.[/dim]")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.lower() == "/quit":
            console.print("[dim]Goodbye! May your draws be legendary.[/dim]")
            break

        if user_input.lower() == "/new":
            agent.reset()
            console.print(Rule("[dim green]New conversation started[/dim green]"))
            continue

        if user_input.lower() == "/help":
            console.print(HELP_TEXT)
            continue

        # Stream the agent response
        console.print()
        console.print("[bold green]Agent:[/bold green]")

        response_chunks = []

        def on_text(chunk: str):
            response_chunks.append(chunk)
            console.print(chunk, end="", highlight=False)

        try:
            agent.chat(
                user_message=user_input,
                on_text=on_text,
                on_tool_use=on_tool_use,
            )
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            continue

        # Add a newline after the streamed response
        console.print()


if __name__ == "__main__":
    run()
