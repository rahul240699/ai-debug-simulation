"""LangGraph graph definition: observe → think → act → record → check_end."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.agents.prompts import SYSTEM_PROMPT, build_turn_message
from src.agents.state import GraphState
from src.agents.tools import TOOL_SCHEMAS, parse_tool_call
from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE
from src.simulation.dungeon_master import (
    advance_turn,
    check_win,
    execute_action,
    get_observation,
    render_grid,
)

logger = logging.getLogger(__name__)

# ── LLM setup ────────────────────────────────────────────────────────────────

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            api_key=OPENAI_API_KEY,
        )
    return _llm


# ── Graph nodes ──────────────────────────────────────────────────────────────


def observe_node(state: GraphState) -> dict[str, Any]:
    """DM provides the active agent with its fog-of-war observation."""
    dungeon = state["dungeon"]
    agent_id = dungeon.active_agent

    obs = get_observation(dungeon, agent_id)

    logger.info(
        "Turn %d | %s observes from (%d,%d)",
        dungeon.turn_number,
        agent_id,
        obs["agent_position"][0],
        obs["agent_position"][1],
    )

    return {
        "current_agent_id": agent_id,
        "observation": obs,
    }


def think_node(state: GraphState) -> dict[str, Any]:
    """LLM decides which tool to call based on the observation."""
    agent_id = state["current_agent_id"]
    obs = state["observation"]

    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(agent_id=agent_id))
    turn_msg = HumanMessage(content=build_turn_message(obs))

    llm = _get_llm()
    response = llm.invoke(
        [system_msg, turn_msg],
        tools=TOOL_SCHEMAS,
        tool_choice="required",
    )

    # Extract tool call from response.
    if response.tool_calls:
        tc = response.tool_calls[0]
        action_name, action_args = parse_tool_call(tc["name"], tc["args"])
    else:
        # Fallback: if the model didn't call a tool, default to wait.
        action_name, action_args = "wait", {}

    logger.info(
        "Turn %d | %s chose %s(%s)",
        state["dungeon"].turn_number,
        agent_id,
        action_name,
        json.dumps(action_args),
    )

    return {
        "action_name": action_name,
        "action_args": action_args,
        "messages": [system_msg, turn_msg, response],
    }


def act_node(state: GraphState) -> dict[str, Any]:
    """Execute the chosen action against the Dungeon Master."""
    dungeon = state["dungeon"]
    agent_id = state["current_agent_id"]

    result = execute_action(
        dungeon, agent_id, state["action_name"], state["action_args"]
    )

    # Check win after action.
    if check_win(dungeon):
        result["game_over"] = True
        result["win"] = True

    logger.info(
        "Turn %d | %s → %s | %s",
        dungeon.turn_number,
        agent_id,
        "OK" if result["success"] else "FAIL",
        result["message"],
    )

    return {"action_result": result}


def record_node(state: GraphState) -> dict[str, Any]:
    """Build an event record for this turn (instrumentation hook point)."""
    dungeon = state["dungeon"]
    agent_id = state["current_agent_id"]

    event: dict[str, Any] = {
        "run_id": dungeon.run_id,
        "turn_number": dungeon.turn_number,
        "agent_id": agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observation": state["observation"],
        "action": state["action_name"],
        "action_args": state["action_args"],
        "action_result": state["action_result"],
        # Placeholders for Phase 3 instrumentation.
        "discrepancy_detected": False,
        "discrepancy_details": None,
    }
    dungeon.event_log.append(event)

    return {}


def check_end_node(state: GraphState) -> dict[str, Any]:
    """Advance to next agent or end the game."""
    dungeon = state["dungeon"]

    # Print grid state.
    print(f"\n--- After Turn {dungeon.turn_number} ({state['current_agent_id']}) ---")
    print(render_grid(dungeon))
    result = state["action_result"]
    print(f"  Action: {result['action']} → {'OK' if result['success'] else 'FAIL'}: {result['message']}")

    advance_turn(dungeon)
    return {}


# ── Routing ──────────────────────────────────────────────────────────────────


def should_continue(state: GraphState) -> Literal["observe", "__end__"]:
    """Decide whether to loop for the next agent or end."""
    dungeon = state["dungeon"]
    if dungeon.game_over:
        print(f"\n{'='*40}")
        print(f"GAME OVER — {'WIN' if dungeon.win else 'LOSS'} after {dungeon.turn_number} turns")
        print(f"{'='*40}\n")
        return "__end__"
    if dungeon.turn_number >= dungeon.max_turns:
        dungeon.game_over = True
        print(f"\n{'='*40}")
        print(f"GAME OVER — Max turns ({dungeon.max_turns}) reached. LOSS.")
        print(f"{'='*40}\n")
        return "__end__"
    return "observe"


# ── Build the graph ──────────────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """Construct and compile the LangGraph dungeon state machine."""
    graph = StateGraph(GraphState)

    graph.add_node("observe", observe_node)
    graph.add_node("think", think_node)
    graph.add_node("act", act_node)
    graph.add_node("record", record_node)
    graph.add_node("check_end", check_end_node)

    graph.set_entry_point("observe")
    graph.add_edge("observe", "think")
    graph.add_edge("think", "act")
    graph.add_edge("act", "record")
    graph.add_edge("record", "check_end")

    graph.add_conditional_edges("check_end", should_continue)

    return graph.compile()
