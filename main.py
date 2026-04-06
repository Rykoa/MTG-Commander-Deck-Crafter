"""
MTG Commander Deck Crafter
Entry point — runs the CLI chat interface.
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from config import ANTHROPIC_API_KEY

def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("Copy .env.example to .env and add your API key.")
        sys.exit(1)

    from ui.cli import run
    run()


if __name__ == "__main__":
    main()
