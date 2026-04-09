"""Tool definitions exposed to the LLM agents.

Each tool is a thin description; actual execution is delegated to the
Dungeon Master via `execute_action`.  The schema here tells the LLM what
it can do and what arguments each action takes.
"""

from __future__ import annotations

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "move",
            "description": (
                "Move one step in a cardinal direction. "
                "Fails if the target cell is a wall or locked door."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["north", "south", "east", "west"],
                        "description": "The direction to move.",
                    }
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pick_up_item",
            "description": (
                "Pick up the key if you are standing on the same cell as the key."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unlock_door",
            "description": (
                "Unlock the locked door if you have the key and are adjacent to the door. "
                "This opens the exit."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": (
                "Send a short text message to the other agent. "
                "The message will be delivered at the START of their NEXT turn (1-turn delay)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The message to send (max 200 chars).",
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Do nothing this turn. Skip your action.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def parse_tool_call(tool_name: str, tool_args: dict) -> tuple[str, dict]:
    """Map an LLM tool call to (action, action_args) for execute_action."""
    if tool_name == "move":
        return "move", {"direction": tool_args.get("direction", "")}
    elif tool_name == "pick_up_item":
        return "pick_up_item", {}
    elif tool_name == "unlock_door":
        return "unlock_door", {}
    elif tool_name == "send_message":
        return "send_message", {"text": tool_args.get("text", "")}
    elif tool_name == "wait":
        return "wait", {}
    else:
        return "wait", {}
