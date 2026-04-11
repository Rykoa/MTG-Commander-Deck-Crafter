"""
MTG Commander Deck Crafter Agent
Claude-powered agent with Scryfall tool use for deck building.
"""

import os
import json
import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, KNOWLEDGE_DIR
from agent.tools.scryfall import SCRYFALL_TOOL_DEFINITIONS, dispatch_tool as scryfall_dispatch
from agent.tools.deck_analyzer import DECK_ANALYZER_TOOL_DEFINITIONS, dispatch_tool as analyzer_dispatch
from agent.tools.spellbook import SPELLBOOK_TOOL_DEFINITIONS, dispatch_tool as spellbook_dispatch
from agent.tools.edhrec import EDHREC_TOOL_DEFINITIONS, dispatch_tool as edhrec_dispatch


def load_system_prompt() -> str:
    path = os.path.join(KNOWLEDGE_DIR, "system_prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class DeckCrafterAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.system_prompt = load_system_prompt()
        self.conversation_history = []
        self.tools = (
            SCRYFALL_TOOL_DEFINITIONS
            + DECK_ANALYZER_TOOL_DEFINITIONS
            + SPELLBOOK_TOOL_DEFINITIONS
            + EDHREC_TOOL_DEFINITIONS
        )
        self._dispatchers = [
            scryfall_dispatch,
            analyzer_dispatch,
            spellbook_dispatch,
            edhrec_dispatch,
        ]

    def _dispatch(self, tool_name: str, tool_input: dict) -> str:
        """Route a tool call to the correct dispatcher."""
        import json
        for dispatcher in self._dispatchers:
            result = dispatcher(tool_name, tool_input)
            parsed = json.loads(result)
            if not (isinstance(parsed, dict) and parsed.get("error", "").startswith("Unknown tool:")):
                return result
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def reset(self):
        """Clear conversation history to start a new session."""
        self.conversation_history = []

    def chat(self, user_message: str, on_text: callable = None, on_tool_use: callable = None) -> str:
        """
        Send a message and get a response.

        Args:
            user_message: The user's input
            on_text: Optional callback(text_chunk) called for each streamed text delta
            on_tool_use: Optional callback(tool_name, tool_input) called when a tool is invoked

        Returns:
            The complete assistant response text
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        full_response_text = ""

        while True:
            # Stream the response
            with self.client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=8192,
                system=self.system_prompt,
                tools=self.tools,
                messages=self.conversation_history,
                thinking={"type": "adaptive"},
            ) as stream:
                # Collect streamed text for display
                current_text = ""
                for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and hasattr(event.delta, "type")
                        and event.delta.type == "text_delta"
                    ):
                        chunk = event.delta.text
                        current_text += chunk
                        if on_text:
                            on_text(chunk)

                response = stream.get_final_message()

            # Append full assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response.content
            })

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Extract all text blocks for the final return value
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        full_response_text += block.text
                break

            if response.stop_reason == "tool_use":
                # Execute all tool calls and collect results
                tool_results = []
                for block in response.content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        if on_tool_use:
                            on_tool_use(tool_name, tool_input)

                        result = self._dispatch(tool_name, tool_input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # Feed results back as a user message and loop
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })
                continue

            # Any other stop reason — extract text and break
            for block in response.content:
                if hasattr(block, "type") and block.type == "text":
                    full_response_text += block.text
            break

        return full_response_text
