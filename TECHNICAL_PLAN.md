# Multi-Agent Dungeon Simulation — Technical Plan

## Overview

A turn-based dungeon simulation where two LLM-powered agents navigate a grid, find a key, and reach an exit. The core value proposition is **observability**: every decision, perception, and belief is captured in structured traces so a human operator can diagnose *why* agents fail — stale beliefs, tool errors, coordination breakdowns, or prompt deficiencies.

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                       │
│              (Diagnosis Dashboard / Legibility UI)           │
├─────────────────────────────────────────────────────────────┤
│                  FastAPI Backend (REST + WS)                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Legibility   │  │  Simulation  │  │  Instrumentation   │  │
│  │ API          │  │  Engine      │  │  (Langfuse)        │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│         │                │                    │              │
│         │         ┌──────┴──────┐             │              │
│         │         │ LangGraph   │─────────────┘              │
│         │         │ Agent Loop  │                            │
│         │         └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow (per turn)

1. **Dungeon Master** provides the active agent with its `observed_state` (adjacent cells only — fog of war).
2. The agent's LangGraph node receives this observation, updates its `internal_belief_model`, produces a `rationale`, and selects a tool (move/pickup/drop/wait).
3. The Dungeon Master validates the action, mutates world state, and returns a `tool_result`.
4. The instrumentation layer compares the agent's expectation against the `tool_result` and flags `discrepancy_detected`.
5. A structured **Event Record** is emitted to Langfuse and cached for the Legibility API.
6. Turn passes to the next agent (round-robin).

---

## 2. LangGraph State Schema

LangGraph uses a typed dict as the graph state. Below is the full schema.

### 2.1 Top-Level Graph State

```python
from typing import TypedDict, Literal
from langgraph.graph import MessagesState

class AgentBeliefModel(TypedDict):
    """What the agent *thinks* the world looks like."""
    grid_knowledge: dict[tuple[int, int], str | None]
    # Maps (row, col) -> last-known content ("empty", "wall", "key", "exit", "unknown")
    key_location: tuple[int, int] | None       # Where agent believes the key is
    exit_location: tuple[int, int] | None       # Where agent believes the exit is
    partner_location: tuple[int, int] | None    # Where agent believes its partner is
    has_key: bool                                # Does *this* agent hold the key?
    partner_has_key: bool                        # Does the agent believe its partner holds the key?
    last_updated_turn: int                       # Turn number of the last belief update

class ObservedState(TypedDict):
    """What the Dungeon Master reveals to the agent this turn."""
    agent_position: tuple[int, int]
    adjacent_cells: dict[str, str]
    # {"north": "empty", "south": "wall", "east": "key", "west": "unknown"}
    visible_entities: list[dict]
    # [{"type": "agent", "id": "agent_b", "position": [2,3]}]
    turn_number: int
    has_key: bool                                # Ground truth for this agent

class ActionResult(TypedDict):
    """Dungeon Master's response to an agent action."""
    success: bool
    action: str                       # "move_north", "pickup_key", etc.
    new_position: tuple[int, int]
    message: str                      # Human-readable outcome
    game_over: bool
    win: bool

class EventRecord(TypedDict):
    """The core observability artifact — one per agent step."""
    run_id: str
    turn_number: int
    agent_id: str
    timestamp: str                    # ISO 8601
    observed_state: ObservedState
    internal_belief_model: AgentBeliefModel
    rationale: str                    # LLM chain-of-thought
    chosen_action: str
    action_result: ActionResult
    discrepancy_detected: bool
    discrepancy_details: str | None   # e.g. "Expected cell (3,2) to be empty but it contained a wall"
    belief_diff: dict | None          # JSON-patch style diff of belief before vs after

class DungeonState(TypedDict):
    """Full world state managed by the Dungeon Master."""
    grid: list[list[str]]             # 2D grid, each cell is a string
    grid_width: int
    grid_height: int
    key_position: tuple[int, int] | None  # None if picked up
    exit_position: tuple[int, int]
    agents: dict[str, AgentState]     # keyed by agent_id
    turn_number: int
    turn_order: list[str]             # ["agent_a", "agent_b"]
    active_agent: str
    game_over: bool
    win: bool
    event_log: list[EventRecord]

class AgentState(TypedDict):
    """Per-agent state within the dungeon."""
    agent_id: str
    position: tuple[int, int]
    has_key: bool
    belief_model: AgentBeliefModel
    message_history: list[dict]       # LangGraph messages
```

### 2.2 LangGraph Graph Nodes

```
START
  │
  ▼
┌──────────────┐
│  observe     │  ← DM provides observed_state to active agent
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  think       │  ← Agent LLM: update beliefs, produce rationale, choose action
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  act         │  ← Execute chosen tool against DM, get ActionResult
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  record      │  ← Build EventRecord, detect discrepancies, emit to Langfuse
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  check_end   │  ← game_over? → END or rotate to next agent → observe
└──────────────┘
```

---

## 3. Custom Langfuse Trace Schema

Every simulation run creates a single **Langfuse Trace**. Within it, each agent turn is a **Span** containing structured metadata.

### 3.1 Trace-Level Metadata

```json
{
  "trace_id": "run_abc123",
  "name": "dungeon_simulation",
  "metadata": {
    "grid_dimensions": [8, 8],
    "num_agents": 2,
    "agent_ids": ["agent_a", "agent_b"],
    "key_position_initial": [2, 5],
    "exit_position": [7, 7],
    "max_turns": 100,
    "model": "gpt-4o-mini",
    "started_at": "2026-04-09T10:00:00Z"
  },
  "tags": ["dungeon", "multi-agent", "observability-demo"]
}
```

### 3.2 Per-Turn Span

Each agent turn produces a span nested under the trace:

```json
{
  "span_id": "turn_007_agent_a",
  "parent_trace_id": "run_abc123",
  "name": "agent_turn",
  "metadata": {
    "turn_number": 7,
    "agent_id": "agent_a",
    "phase": "full_turn"
  },
  "input": {
    "observed_state": {
      "agent_position": [3, 4],
      "adjacent_cells": {
        "north": "empty",
        "south": "wall",
        "east": "key",
        "west": "empty"
      },
      "visible_entities": [
        { "type": "agent", "id": "agent_b", "position": [3, 5] }
      ],
      "turn_number": 7,
      "has_key": false
    },
    "belief_model_before": {
      "grid_knowledge": { "(3,4)": "empty", "(2,5)": "key" },
      "key_location": [2, 5],
      "exit_location": [7, 7],
      "partner_location": [1, 1],
      "has_key": false,
      "partner_has_key": false,
      "last_updated_turn": 5
    }
  },
  "output": {
    "rationale": "I can see a key to my east at (3,5). My belief said the key was at (2,5) — this is stale. I should move east to pick up the key.",
    "chosen_action": "move_east",
    "action_result": {
      "success": true,
      "action": "move_east",
      "new_position": [3, 5],
      "message": "Moved east to (3,5).",
      "game_over": false,
      "win": false
    },
    "belief_model_after": {
      "grid_knowledge": { "(3,4)": "empty", "(3,5)": "key" },
      "key_location": [3, 5],
      "exit_location": [7, 7],
      "partner_location": [3, 5],
      "has_key": false,
      "partner_has_key": false,
      "last_updated_turn": 7
    },
    "discrepancy_detected": true,
    "discrepancy_details": "Belief had key at (2,5) but observed key at (3,5). Belief stale by 2 turns.",
    "belief_diff": [
      { "op": "replace", "path": "/key_location", "from": [2, 5], "to": [3, 5] },
      { "op": "replace", "path": "/partner_location", "from": [1, 1], "to": [3, 5] }
    ]
  },
  "level": "DEFAULT",
  "status_message": "discrepancy_detected"
}
```

### 3.3 LLM Generation (nested inside the turn span)

```json
{
  "generation_id": "gen_turn7_agent_a",
  "parent_span_id": "turn_007_agent_a",
  "name": "agent_reasoning",
  "model": "gpt-4o-mini",
  "input": [
    {
      "role": "system",
      "content": "You are Agent A in a dungeon. Your goal is to find the key and reach the exit..."
    },
    {
      "role": "user",
      "content": "Turn 7. You are at (3,4). Adjacent: north=empty, south=wall, east=key, west=empty. You see Agent B at (3,5). You do NOT have the key."
    }
  ],
  "output": {
    "role": "assistant",
    "content": "{ \"rationale\": \"I see a key to my east...\", \"action\": \"move_east\" }"
  },
  "usage": { "prompt_tokens": 340, "completion_tokens": 85 },
  "metadata": { "temperature": 0.2 }
}
```

---

## 4. Dungeon Master — Stale Information Logic

The Dungeon Master (DM) is **not** an LLM agent. It is deterministic Python code that manages world state and enforces fog-of-war. Stale information arises naturally from the design:

### 4.1 Fog of War Rules

| Rule | Detail |
|---|---|
| **Vision radius** | Each agent sees only its own cell and the 4 orthogonal neighbors (Von Neumann neighborhood, radius 1). |
| **No memory sharing** | Agents do NOT share observations. Agent A never directly sees what Agent B saw. |
| **Belief persistence** | An agent's `grid_knowledge` retains old values for cells not currently visible. These can become stale. |
| **World mutation** | The DM can move items or change the grid between turns (e.g., a door closes). This makes previously-correct beliefs stale. |

### 4.2 Stale Information Scenarios (Engineered for Demo)

1. **Key Relocation**: After N turns, the DM moves the key to a new position. An agent that saw the key earlier has stale `key_location`. When it arrives at the old location, `discrepancy_detected = true`.

2. **Closing Door**: A previously-open cell becomes a wall. Agent moves toward it based on stale info, action fails.

3. **Partner Drift**: Agent A last saw Agent B at (1,1) on turn 3. By turn 7, Agent B is at (5,5). Agent A's `partner_location` is stale by 4 turns.

4. **False Key Belief**: Agent A's partner picked up the key, but Agent A still believes `key_location = (2,5)` and `partner_has_key = false`.

### 4.3 Discrepancy Detection Algorithm

After every action, the `record` node runs:

```python
def detect_discrepancies(
    belief_before: AgentBeliefModel,
    observed_state: ObservedState,
    action_result: ActionResult,
) -> tuple[bool, str | None, dict | None]:
    discrepancies = []
    diff = []

    # 1. Check if observed cells contradict beliefs
    for direction, content in observed_state["adjacent_cells"].items():
        cell_pos = direction_to_position(observed_state["agent_position"], direction)
        believed = belief_before["grid_knowledge"].get(cell_pos, "unknown")
        if believed != "unknown" and believed != content:
            discrepancies.append(
                f"Belief: {cell_pos}={believed}, Observed: {content}"
            )
            diff.append({"op": "replace", "path": f"/grid_knowledge/{cell_pos}", "from": believed, "to": content})

    # 2. Check if action failed unexpectedly
    if not action_result["success"]:
        discrepancies.append(f"Action '{action_result['action']}' failed: {action_result['message']}")

    # 3. Check key location consistency
    if belief_before["key_location"]:
        key_pos = belief_before["key_location"]
        if key_pos in get_visible_cells(observed_state):
            actual_content = get_cell_content(observed_state, key_pos)
            if actual_content != "key":
                discrepancies.append(f"Key expected at {key_pos} but found '{actual_content}'")
                diff.append({"op": "replace", "path": "/key_location", "from": list(key_pos), "to": None})

    detected = len(discrepancies) > 0
    details = "; ".join(discrepancies) if detected else None
    return detected, details, diff if diff else None
```

---

## 5. Legibility Layer — Diagnosis Dashboard UI

### 5.1 Design Philosophy

The dashboard answers three questions:
- **What happened?** → Event Timeline
- **Why did it happen?** → Causal Chain Viewer
- **What should change?** → Diagnosis Panel

### 5.2 UI Components

#### Page: Run Selector (`/`)

| Component | Description |
|---|---|
| **Run List** | Table of past simulation runs with columns: Run ID, Date, Outcome (win/loss), Turns, Discrepancies Count. Click to open. |

#### Page: Run Dashboard (`/runs/:id`)

The main diagnosis workspace. Four panels:

---

##### Panel 1: Grid Visualizer (top-left)

- **Animated grid** showing the dungeon at a given turn.
- Agent positions shown as colored icons (Agent A = blue, Agent B = orange).
- Key and exit marked with distinct icons.
- **Fog-of-war overlay**: cells not visible to the selected agent are dimmed.
- **Belief overlay toggle**: switch between "ground truth" and "Agent X's belief" to see what the agent *thinks* vs. reality. Stale cells highlighted in red.
- **Turn scrubber**: slider to step through turns.

##### Panel 2: Event Timeline (top-right)

- Vertical scrolling timeline, one card per turn.
- Each card shows:
  - Turn number + agent ID.
  - Chosen action + result (success/fail icon).
  - Discrepancy badge (red dot) if `discrepancy_detected`.
  - Expandable: full rationale text, belief diff, observed state.
- Click a card to sync the Grid Visualizer to that turn.

##### Panel 3: Belief Inspector (bottom-left)

- Side-by-side comparison for the selected turn:
  - **Left column**: Agent's `internal_belief_model` (what it thinks).
  - **Right column**: Ground truth `DungeonState` (what actually is).
- Differences highlighted with color coding.
- Shows `belief_diff` as a JSON-patch view.
- **Staleness indicator**: "Key location belief is N turns stale."

##### Panel 4: Diagnosis Panel (bottom-right)

- Automated analysis of failure modes for the selected run.
- Categories:
  - **Prompt Issue**: Agent had correct info but chose wrong action → prompt/reasoning failure.
  - **Tool Issue**: Agent chose correct action but it failed → tool/environment failure.
  - **Coordination Issue**: One agent undid or conflicted with the other's plan.
  - **Stale Info Issue**: Agent acted on outdated beliefs (most common).
- Each diagnosis links back to the specific turns that caused it.
- **Summary stats**: Total discrepancies, average belief staleness, turns wasted on stale info.

### 5.3 API Endpoints (Legibility)

| Endpoint | Method | Description |
|---|---|---|
| `/api/runs` | GET | List all runs with summary stats |
| `/api/runs/:id` | GET | Full run metadata |
| `/api/runs/:id/events` | GET | All EventRecords for a run |
| `/api/runs/:id/events/:turn` | GET | Single turn's EventRecord |
| `/api/runs/:id/grid/:turn` | GET | Grid state at a specific turn (ground truth) |
| `/api/runs/:id/beliefs/:agent/:turn` | GET | Agent's belief model at a specific turn |
| `/api/runs/:id/diagnosis` | GET | Automated diagnosis summary |
| `/api/runs/:id/discrepancies` | GET | All discrepancy events with causal links |
| `/ws/runs/:id/live` | WS | Live streaming of events during an active run |

---

## 6. Repository Structure

```
prove-ai-assignment/
├── README.md
├── pyproject.toml
├── .env.example
│
├── src/
│   ├── __init__.py
│   ├── config.py                         # Env vars, settings
│   ├── main.py                           # FastAPI app entrypoint
│   │
│   ├── simulation/                       # Core dungeon logic
│   │   ├── __init__.py
│   │   ├── grid.py                       # Grid creation, cell types
│   │   ├── dungeon_master.py             # DM logic, fog-of-war, world mutation
│   │   ├── items.py                      # Key, Exit, Wall definitions
│   │   ├── state.py                      # DungeonState, AgentState TypedDicts
│   │   └── scenarios.py                  # Pre-built stale-info scenarios
│   │
│   ├── agents/                           # LangGraph agent definitions
│   │   ├── __init__.py
│   │   ├── graph.py                      # LangGraph graph definition + nodes
│   │   ├── state.py                      # Agent-specific state schemas
│   │   ├── tools.py                      # Tool definitions (move, pickup, etc.)
│   │   ├── prompts.py                    # System & turn prompts
│   │   └── belief.py                     # Belief model update logic
│   │
│   ├── instrumentation/                  # Observability layer
│   │   ├── __init__.py
│   │   ├── langfuse_client.py            # Langfuse SDK wrapper
│   │   ├── event_schema.py              # EventRecord, ObservedState TypedDicts
│   │   ├── discrepancy.py               # Discrepancy detection logic
│   │   └── trace_builder.py             # Helpers to build structured spans
│   │
│   └── legibility/                       # Diagnosis API layer
│       ├── __init__.py
│       ├── router.py                     # FastAPI router for /api/runs/*
│       ├── diagnosis.py                  # Automated failure-mode analysis
│       └── schemas.py                    # Pydantic response models
│
├── frontend/                             # Next.js Diagnosis Dashboard
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                  # Run Selector
│   │   │   └── runs/
│   │   │       └── [id]/
│   │   │           └── page.tsx          # Run Dashboard
│   │   │
│   │   ├── components/
│   │   │   ├── GridVisualizer.tsx
│   │   │   ├── EventTimeline.tsx
│   │   │   ├── BeliefInspector.tsx
│   │   │   ├── DiagnosisPanel.tsx
│   │   │   └── TurnScrubber.tsx
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                    # Fetch wrappers for backend API
│   │   │   └── types.ts                  # TypeScript equivalents of schemas
│   │   │
│   │   └── hooks/
│   │       ├── useRunData.ts
│   │       └── useLiveStream.ts
│   │
│   └── public/
│       └── icons/                        # Agent, key, exit icons
│
├── tests/
│   ├── __init__.py
│   ├── test_grid.py
│   ├── test_dungeon_master.py
│   ├── test_discrepancy.py
│   └── test_diagnosis.py
│
└── docs/
    └── TECHNICAL_PLAN.md                 # → This file (symlinked or copied)
```

---

## 7. Development Phases

| Phase | Focus | Deliverables |
|---|---|---|
| **Phase 1** | World Simulation | Grid, DM, items, fog-of-war, state management. Playable via CLI with random/scripted moves. |
| **Phase 2** | Agent Intelligence | LangGraph graph, LLM integration, belief model, tool definitions. Agents can play autonomously. |
| **Phase 3** | Instrumentation | Langfuse integration, EventRecord emission, discrepancy detection. Full traces captured. |
| **Phase 4** | Legibility Layer | FastAPI diagnosis endpoints, diagnosis algorithm, Pydantic schemas. |
| **Phase 5** | Frontend Dashboard | Next.js UI with all four panels, live streaming, belief overlay. |
| **Phase 6** | Polish & Demo | Pre-built scenarios, demo script, error injection toggles. |

---

## 8. Key Dependencies

### Python (Backend)
```
fastapi>=0.115
uvicorn>=0.30
langgraph>=0.4
langchain-openai>=0.3
langfuse>=2.50
pydantic>=2.10
python-dotenv>=1.0
websockets>=13.0
```

### Node.js (Frontend)
```
next@15
react@19
tailwindcss@4
typescript@5
```

---

*Awaiting approval before proceeding to Phase 1 implementation.*
