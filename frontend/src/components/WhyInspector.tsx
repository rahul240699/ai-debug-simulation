/** Why Inspector — split-view: agent belief vs actual world state.
 *  Enhanced with:
 *  - Full-size grid visualiser with agent/partner/discrepancy highlights
 *  - Belief staleness amber warnings (>3 turns old)
 */

import type { CriticalEvent, EventRecord } from "@/lib/types";

interface Props {
  event: EventRecord | null;
  timelineEvent: CriticalEvent | null;
  gridSize?: string;          // e.g. "8x8"
}

export function WhyInspector({ event, timelineEvent, gridSize }: Props) {
  if (!event || !timelineEvent) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg h-full flex items-center justify-center min-h-[400px]">
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
  const currentTurn = event.turn_number;
  const beliefAge = belief.last_updated_turn >= 0 ? currentTurn - belief.last_updated_turn : -1;

  // Parse grid dimensions
  const [gridW, gridH] = (gridSize ?? "8x8").split("x").map(Number);

  // Find partner pos from observed entities
  const partnerEntity = obs.visible_entities.find(
    (e) => e.type === "agent" && e.id !== event.agent_id
  );
  const partnerPos = partnerEntity ? partnerEntity.position : null;

  // Find discrepancy target position if applicable
  const discTarget = parseDiscrepancyTarget(event.discrepancy_details);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700/50">
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
                : "bg-rose-500/10 text-rose-400"
            }`}
          >
            {result.success ? "OK" : "FAILED"}
          </span>
        </div>
      </div>

      {/* Discrepancy banner */}
      {event.discrepancy_detected && event.discrepancy_details && (
        <div className="mx-4 mt-3 p-3 bg-rose-500/5 border border-rose-600/20 rounded-md">
          <p className="text-xs font-semibold text-rose-400 mb-1">⚠ Discrepancy Detected</p>
          <p className="text-xs text-rose-300/80 leading-relaxed">{event.discrepancy_details}</p>
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
      <div className="grid grid-cols-2 gap-px bg-slate-700/30 mt-3">
        {/* Left: What the agent believed */}
        <div className="bg-slate-800/50 p-4">
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
            stale={belief.key_location !== null && beliefAge > 3}
          />
          <DataRow
            label="Partner Location"
            value={
              belief.partner_location
                ? `(${belief.partner_location[0]}, ${belief.partner_location[1]})`
                : "Unknown"
            }
            stale={belief.partner_location !== null && beliefAge > 3}
          />
          <DataRow
            label="Partner Has Key"
            value={belief.partner_has_key ? "Yes" : "No"}
            stale={beliefAge > 3}
          />
          <DataRow
            label="Last Updated"
            value={belief.last_updated_turn >= 0 ? `Turn ${belief.last_updated_turn}` : "Never"}
            stale={beliefAge > 3}
            staleSuffix={beliefAge > 3 ? `${beliefAge} turns ago` : undefined}
          />
          <div className="mt-3">
            <p className="text-xs text-zinc-500 mb-1">
              Known cells: {Object.keys(belief.grid_knowledge).length}
            </p>
            <EnhancedGrid
              gridW={gridW}
              gridH={gridH}
              knowledge={belief.grid_knowledge}
              agentPos={obs.agent_position}
              partnerPos={belief.partner_location}
              discrepancyPos={discTarget}
              label="belief"
            />
          </div>
        </div>

        {/* Right: What was actually true */}
        <div className="bg-slate-800/50 p-4">
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
      <div className="px-4 py-3 border-t border-slate-700/50">
        <p className="text-xs text-zinc-400">
          <span className="text-zinc-500">Result:</span> {result.message}
        </p>
      </div>
    </div>
  );
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function parseDiscrepancyTarget(details: string | null): number[] | null {
  if (!details) return null;
  // Look for patterns like "at (3,4)" or "expected at (1,2)"
  const match = details.match(/at \((\d+),\s*(\d+)\)/);
  if (match) return [parseInt(match[1]), parseInt(match[2])];
  return null;
}

function DataRow({
  label,
  value,
  highlight,
  stale,
  staleSuffix,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  stale?: boolean;
  staleSuffix?: string;
}) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-xs text-zinc-500">{label}</span>
      <div className="flex items-center gap-1.5">
        {stale && (
          <span className="text-[10px] text-amber-400" title={staleSuffix ?? "Data is stale (>3 turns old)"}>
            ⏳
          </span>
        )}
        <span className={`text-xs font-mono ${
          stale ? "text-amber-300" : highlight ? "text-amber-300" : "text-zinc-300"
        }`}>
          {value}
        </span>
        {staleSuffix && (
          <span className="text-[10px] text-amber-500/70">{staleSuffix}</span>
        )}
      </div>
    </div>
  );
}

function CellBadge({ cell }: { cell: string }) {
  const colors: Record<string, string> = {
    empty: "bg-zinc-800 text-zinc-400",
    wall: "bg-zinc-700 text-zinc-300",
    key: "bg-amber-500/20 text-amber-400",
    locked_door: "bg-rose-500/20 text-rose-400",
    exit: "bg-emerald-500/20 text-emerald-400",
  };

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${colors[cell] ?? "bg-zinc-800 text-zinc-400"}`}>
      {cell}
    </span>
  );
}

/** Enhanced full-size grid visualiser */
function EnhancedGrid({
  gridW,
  gridH,
  knowledge,
  agentPos,
  partnerPos,
  discrepancyPos,
  label,
}: {
  gridW: number;
  gridH: number;
  knowledge: Record<string, string>;
  agentPos: number[];
  partnerPos?: number[] | null;
  discrepancyPos?: number[] | null;
  label: string;
}) {
  const CELL_COLORS: Record<string, string> = {
    empty: "bg-zinc-800/80",
    wall: "bg-zinc-600",
    key: "bg-amber-500",
    locked_door: "bg-rose-500",
    exit: "bg-emerald-500",
  };

  // Determine cell size based on grid dimension
  const maxDim = Math.max(gridW, gridH);
  const cellPx = maxDim > 12 ? 10 : maxDim > 8 ? 12 : 14;

  return (
    <div
      className="inline-grid gap-px"
      style={{ gridTemplateColumns: `repeat(${gridW}, ${cellPx}px)` }}
    >
      {Array.from({ length: gridH }, (_, ri) =>
        Array.from({ length: gridW }, (_, ci) => {
          const key = `${ri},${ci}`;
          const cell = knowledge[key];
          const isAgent = ri === agentPos[0] && ci === agentPos[1];
          const isPartner = partnerPos && ri === partnerPos[0] && ci === partnerPos[1];
          const isDisc = discrepancyPos && ri === discrepancyPos[0] && ci === discrepancyPos[1];

          let cls: string;
          let content = "";

          if (isAgent) {
            cls = "bg-blue-400 ring-1 ring-blue-300";
          } else if (isPartner) {
            cls = "bg-orange-400 ring-1 ring-orange-300";
          } else if (isDisc) {
            cls = "bg-rose-600 ring-1 ring-rose-400";
            content = "✕";
          } else if (cell) {
            cls = CELL_COLORS[cell] ?? "bg-zinc-800";
          } else {
            cls = "bg-zinc-900/60";
          }

          const title = [
            `(${ri},${ci})`,
            cell ?? "unknown",
            isAgent ? `[${label === "belief" ? "you" : "agent"}]` : "",
            isPartner ? "[partner]" : "",
            isDisc ? "[discrepancy]" : "",
          ].filter(Boolean).join(" · ");

          return (
            <div
              key={key}
              className={`rounded-sm flex items-center justify-center ${cls}`}
              style={{ width: cellPx, height: cellPx }}
              title={title}
            >
              {content && (
                <span className="text-[8px] text-white font-bold leading-none">{content}</span>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
