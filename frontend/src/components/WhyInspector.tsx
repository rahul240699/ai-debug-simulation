/** Why Inspector — split-view: agent belief vs actual world state. */

import type { CriticalEvent, EventRecord } from "@/lib/types";

interface Props {
  event: EventRecord | null;
  timelineEvent: CriticalEvent | null;
}

export function WhyInspector({ event, timelineEvent }: Props) {
  if (!event || !timelineEvent) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg h-full flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-zinc-500 text-sm">Select an event from the timeline</p>
          <p className="text-zinc-600 text-xs mt-1">to inspect the belief vs reality split</p>
        </div>
      </div>
    );
  }

  const belief = event.belief_before;
  const obs = event.observed_state;
  const result = event.action_result;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-300">Why Inspector</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-500">Turn {event.turn_number}</span>
            <span
              className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                event.agent_id === "agent_a"
                  ? "bg-blue-500/10 text-blue-400"
                  : "bg-orange-500/10 text-orange-400"
              }`}
            >
              {event.agent_id === "agent_a" ? "Agent A" : "Agent B"}
            </span>
          </div>
        </div>
        {/* Action summary */}
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-zinc-400">
            Action: <code className="text-zinc-300">{event.chosen_action}</code>
            {event.action_args && Object.keys(event.action_args).length > 0 && (
              <span className="text-zinc-500">
                ({Object.entries(event.action_args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})
              </span>
            )}
          </span>
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              result.success
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-red-500/10 text-red-400"
            }`}
          >
            {result.success ? "OK" : "FAILED"}
          </span>
        </div>
      </div>

      {/* Discrepancy banner */}
      {event.discrepancy_detected && event.discrepancy_details && (
        <div className="mx-4 mt-3 p-3 bg-red-500/5 border border-red-500/20 rounded-md">
          <p className="text-xs font-semibold text-red-400 mb-1">⚠ Discrepancy Detected</p>
          <p className="text-xs text-red-300/80 leading-relaxed">{event.discrepancy_details}</p>
        </div>
      )}

      {/* DM Oracle section */}
      {event.dm_query && (
        <div className="mx-4 mt-3 p-3 bg-purple-500/5 border border-purple-500/20 rounded-md">
          <p className="text-xs font-semibold text-purple-400 mb-1">
            🔮 DM Oracle Query
            {event.dm_stale_turns_count !== null && event.dm_stale_turns_count > 0 && (
              <span className="ml-2 text-amber-400 font-normal">
                ({event.dm_stale_turns_count} turns stale)
              </span>
            )}
          </p>
          <p className="text-xs text-zinc-400">Q: &quot;{event.dm_query}&quot;</p>
          {event.dm_advice && (
            <p className="text-xs text-purple-300/80 mt-1">A: &quot;{event.dm_advice}&quot;</p>
          )}
        </div>
      )}

      {/* Split view: Belief vs Reality */}
      <div className="grid grid-cols-2 gap-px bg-zinc-800 mt-3">
        {/* Left: What the agent believed */}
        <div className="bg-zinc-900 p-4">
          <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-3">
            Agent&apos;s Belief
          </h4>
          <DataRow label="Position" value={`(${obs.agent_position[0]}, ${obs.agent_position[1]})`} />
          <DataRow label="Has Key" value={belief.has_key ? "Yes" : "No"} />
          <DataRow
            label="Key Location"
            value={
              belief.key_location
                ? `(${belief.key_location[0]}, ${belief.key_location[1]})`
                : "Unknown"
            }
            highlight={belief.key_location !== null}
          />
          <DataRow
            label="Partner Location"
            value={
              belief.partner_location
                ? `(${belief.partner_location[0]}, ${belief.partner_location[1]})`
                : "Unknown"
            }
          />
          <DataRow
            label="Partner Has Key"
            value={belief.partner_has_key ? "Yes" : "No"}
          />
          <DataRow
            label="Last Updated"
            value={belief.last_updated_turn >= 0 ? `Turn ${belief.last_updated_turn}` : "Never"}
          />
          <div className="mt-3">
            <p className="text-xs text-zinc-500 mb-1">
              Known cells: {Object.keys(belief.grid_knowledge).length}
            </p>
            <MiniGrid knowledge={belief.grid_knowledge} agentPos={obs.agent_position} />
          </div>
        </div>

        {/* Right: What was actually true */}
        <div className="bg-zinc-900 p-4">
          <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wide mb-3">
            Actual World
          </h4>
          <DataRow label="Position" value={`(${obs.agent_position[0]}, ${obs.agent_position[1]})`} />
          <DataRow label="Current Cell" value={obs.current_cell} />
          <DataRow label="Has Key" value={obs.has_key ? "Yes" : "No"} />
          <div className="mt-2">
            <p className="text-xs text-zinc-500 mb-1">Adjacent Cells</p>
            <div className="grid grid-cols-2 gap-1">
              {Object.entries(obs.adjacent_cells).map(([dir, cell]) => (
                <div key={dir} className="flex items-center gap-1.5">
                  <span className="text-xs text-zinc-600 w-10">{dir}</span>
                  <CellBadge cell={cell} />
                </div>
              ))}
            </div>
          </div>
          {obs.visible_entities.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-zinc-500 mb-1">Visible Entities</p>
              {obs.visible_entities.map((e) => (
                <p key={e.id} className="text-xs text-zinc-400">
                  {e.id} at ({e.position[0]}, {e.position[1]})
                </p>
              ))}
            </div>
          )}
          {obs.messages_received && obs.messages_received.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-zinc-500 mb-1">Messages</p>
              {obs.messages_received.map((m, i) => (
                <p key={i} className="text-xs text-zinc-400">
                  From {m.from}: &quot;{m.text}&quot;
                </p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Result message */}
      <div className="px-4 py-3 border-t border-zinc-800">
        <p className="text-xs text-zinc-400">
          <span className="text-zinc-500">Result:</span> {result.message}
        </p>
      </div>
    </div>
  );
}

function DataRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={`text-xs font-mono ${highlight ? "text-amber-300" : "text-zinc-300"}`}>
        {value}
      </span>
    </div>
  );
}

function CellBadge({ cell }: { cell: string }) {
  const colors: Record<string, string> = {
    empty: "bg-zinc-800 text-zinc-400",
    wall: "bg-zinc-700 text-zinc-300",
    key: "bg-amber-500/20 text-amber-400",
    locked_door: "bg-red-500/20 text-red-400",
    exit: "bg-emerald-500/20 text-emerald-400",
  };

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${colors[cell] ?? "bg-zinc-800 text-zinc-400"}`}>
      {cell}
    </span>
  );
}

function MiniGrid({
  knowledge,
  agentPos,
}: {
  knowledge: Record<string, string>;
  agentPos: number[];
}) {
  // Build a small grid from known cells
  const cells = Object.entries(knowledge);
  if (cells.length === 0) return <p className="text-xs text-zinc-600">No cells explored</p>;

  // Find bounds
  let minR = Infinity, maxR = -Infinity, minC = Infinity, maxC = -Infinity;
  for (const [key] of cells) {
    const [r, c] = key.split(",").map(Number);
    minR = Math.min(minR, r);
    maxR = Math.max(maxR, r);
    minC = Math.min(minC, c);
    maxC = Math.max(maxC, c);
  }

  // Clamp to reasonable size
  const rows = Math.min(maxR - minR + 1, 10);
  const cols = Math.min(maxC - minC + 1, 10);

  const CELL_COLORS: Record<string, string> = {
    empty: "bg-zinc-800",
    wall: "bg-zinc-600",
    key: "bg-amber-500",
    locked_door: "bg-red-500",
    exit: "bg-emerald-500",
  };

  return (
    <div className="inline-grid gap-px" style={{ gridTemplateColumns: `repeat(${cols}, 12px)` }}>
      {Array.from({ length: rows }, (_, ri) =>
        Array.from({ length: cols }, (_, ci) => {
          const r = minR + ri;
          const c = minC + ci;
          const key = `${r},${c}`;
          const cell = knowledge[key];
          const isAgent = r === agentPos[0] && c === agentPos[1];

          return (
            <div
              key={key}
              className={`w-3 h-3 rounded-sm ${
                isAgent
                  ? "bg-blue-400 ring-1 ring-blue-300"
                  : cell
                    ? CELL_COLORS[cell] ?? "bg-zinc-800"
                    : "bg-zinc-900"
              }`}
              title={`(${r},${c}): ${cell ?? "unknown"}`}
            />
          );
        })
      )}
    </div>
  );
}
