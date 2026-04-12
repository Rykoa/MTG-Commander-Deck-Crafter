"""
MTG Commander Deck Crafter — CLI Interface
Rich-formatted terminal chat with the deck building agent.
"""

import re
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from agent.agent import DeckCrafterAgent
from agent.tools.deck_analyzer import analyze_deck

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
  [yellow]/paste[/yellow]    — Paste a full decklist for analysis
  [yellow]/quit[/yellow]     — Exit the program
  [yellow]/help[/yellow]     — Show this help message

[bold cyan]Tips:[/bold cyan]
  • Use [yellow]/paste[/yellow] for deck analysis — paste your Archidekt export, then press Enter on an empty line
  • Ctrl+C cancels any in-progress operation and returns to the prompt
  • Ask anything: build, analyse, find cards, check prices, explain combos
"""


# ── Input helpers ─────────────────────────────────────────────────────────────

def read_multiline_input(console: Console) -> str:
    """
    Wait silently for a pasted decklist. Nothing is printed or processed
    until the user presses Enter on an empty line. Ctrl+C cancels.
    """
    console.print("[dim cyan]Paste your decklist and press Enter when done.[/dim cyan]")
    lines = []
    while True:
        try:
            line = input()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/dim]")
            return ""
        except EOFError:
            break
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _count_card_lines(text: str) -> int:
    """Count lines that look like card entries (with or without a quantity prefix)."""
    card_line = re.compile(r'^\d+x?\s+\w|^[A-Z][a-zA-Z\s,\'\-/]+$')
    return sum(
        1 for l in text.splitlines()
        if l.strip() and card_line.match(l.strip())
        and not re.search(r'\(\d+\)\s*$', l.strip())  # exclude section headers
    )


# ── Deck pre-computation ──────────────────────────────────────────────────────

def _build_analysis_prompt(raw_text: str) -> tuple[str, int] | tuple[None, int]:
    """
    Run analyze_deck locally and return (prompt_string, card_count).
    Returns (None, 0) on failure — caller must handle this explicitly.
    Raises no exceptions.
    """
    lines = [l for l in raw_text.strip().splitlines() if l.strip()]
    try:
        result = analyze_deck(lines)
    except Exception as e:
        return None, 0

    if "error" in result:
        return None, 0

    total = result.get("total_cards_analyzed", 0)
    not_found = result.get("not_found", [])
    rec_lines = "\n".join(f"  - {r}" for r in result.get("recommendations", []))
    curve = result.get("mana_curve", {})
    curve_str = "  " + "  ".join(f"CMC {k}: {v}" for k, v in curve.items() if v > 0)
    colors = result.get("color_distribution", {})
    color_str = ", ".join(f"{c}: {v['percent']}%" for c, v in colors.items()) if colors else "N/A"
    cats = result.get("categories", {})
    cat_str = ", ".join(f"{k}: {v['count']}" for k, v in cats.items() if v["count"] > 0)

    not_found_str = f", {len(not_found)} not found: {', '.join(not_found[:5])}" if not_found else ""

    prompt = (
        f"Please analyse my Commander deck and give detailed recommendations.\n"
        f"[PRE-COMPUTED ANALYSIS — do not call any deck tools]\n"
        f"Cards analysed: {total}{not_found_str}\n"
        f"Lands: {result['lands']['count']}\n"
        f"Avg CMC (non-land): {result['average_cmc']} — {result['cmc_assessment']}\n"
        f"Color pip distribution: {color_str}\n"
        f"Mana curve: {curve_str}\n"
        f"Category counts: {cat_str}\n"
        f"Recommendations:\n{rec_lines}\n"
        f"[END ANALYSIS]"
    )
    return prompt, total



# ── Spinner helpers ───────────────────────────────────────────────────────────

def _make_spinner(text: str, style: str = "dots") -> Live:
    return Live(
        Spinner(style, text=f" [dim cyan]{text}[/dim cyan]"),
        console=console,
        refresh_per_second=12,
        transient=True,
    )


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    console.print(BANNER, style="bold green")
    console.print(
        Panel(
            "[white]Your personal MTG Commander deck building assistant.\n"
            "Type [yellow]/help[/yellow] for commands or just start chatting![/white]",
            border_style="green",
        )
    )

    agent = DeckCrafterAgent()

    while True:
        try:
            console.print()
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye! May your draws be legendary.[/dim]")
            break

        if not user_input:
            continue

        # ── Built-in commands ──────────────────────────────────────────────
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

        # ── /paste — multi-line decklist input ────────────────────────────
        if user_input.lower() == "/paste":
            raw = read_multiline_input(console)
            if not raw:
                continue

            # Show the pasted content and card count for review before processing.
            card_count = _count_card_lines(raw)
            console.print()
            console.print(raw, style="dim")
            console.print()
            console.print(
                f"[bold]{card_count} cards detected.[/bold] "
                f"Press [bold]Enter[/bold] to analyse or [bold]Ctrl+C[/bold] to cancel."
            )
            try:
                input()
            except KeyboardInterrupt:
                console.print("\n[dim]Cancelled.[/dim]")
                continue

            # Phase 1 animation: processing cards locally
            analysis_prompt = None
            with _make_spinner("Processing cards...", "arc"):
                try:
                    analysis_prompt, analysed_count = _build_analysis_prompt(raw)
                except KeyboardInterrupt:
                    console.print("\n[dim]Cancelled.[/dim]")
                    continue

            if analysis_prompt is None:
                console.print(
                    "[bold red]Could not analyse the decklist.[/bold red] "
                    "Check the format and try again."
                )
                continue

            console.print(
                f"[dim green]✓ {analysed_count} cards analysed. "
                f"Generating recommendations...[/dim green]"
            )

            # Phase 2: Claude interprets the pre-computed stats
            console.print()
            console.print("[bold green]Agent:[/bold green]")

            with _make_spinner("Thinking...", "dots") as thinking:
                thinking_active = True

                def stop_thinking():
                    nonlocal thinking_active
                    if thinking_active:
                        thinking.stop()
                        thinking_active = False

                def on_text_analysis(chunk: str):
                    stop_thinking()
                    console.print(chunk, end="", highlight=False)

                try:
                    agent.chat(
                        user_message=analysis_prompt,
                        on_text=on_text_analysis,
                        on_tool_use=lambda n, i: None,  # no tools in analysis mode
                        precomputed=True,
                    )
                except KeyboardInterrupt:
                    console.print("\n[dim]Cancelled.[/dim]")
                except Exception as e:
                    console.print(f"\n[bold red]Error:[/bold red] {e}")
                finally:
                    stop_thinking()

            console.print()
            continue

        # ── Normal chat ───────────────────────────────────────────────────
        console.print()
        console.print("[bold green]Agent:[/bold green]")

        with _make_spinner("Thinking...", "dots") as thinking:
            thinking_active = True

            def stop_thinking():
                nonlocal thinking_active
                if thinking_active:
                    thinking.stop()
                    thinking_active = False

            def on_text(chunk: str):
                stop_thinking()
                console.print(chunk, end="", highlight=False)

            # Tool calls run silently — spinner stays up, no per-tool output.
            # The user only sees the final response.
            def on_tool_use_wrapped(tool_name: str, tool_input: dict):
                pass

            try:
                agent.chat(
                    user_message=user_input,
                    on_text=on_text,
                    on_tool_use=on_tool_use_wrapped,
                )
            except KeyboardInterrupt:
                console.print("\n[dim]Cancelled.[/dim]")
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")
            finally:
                stop_thinking()

        console.print()


if __name__ == "__main__":
    run()
