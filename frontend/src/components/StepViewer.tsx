"use client";

import { useState, useCallback, useEffect } from "react";
import type { EventRecord } from "@/lib/types";

interface Props {
  events: EventRecord[];
}

export function StepViewer({ events }: Props) {
  const [step, setStep] = useState(0);

  const prev = useCallback(() => setStep((s) => Math.max(0, s - 1)), []);
  const next = useCallback(() => setStep((s) => Math.min(events.length - 1, s + 1)), [events.length]);

  // Keyboard navigation
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [prev, next]);

  if (events.length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 text-center">
        <p className="text-zinc-500 text-sm">No events to display</p>
      </div>
    );
  }

  const ev = events[step];
  const belief = ev.belief_before;
  const obs = ev.observed_state;
  const result = ev.action_result;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
      {/* Step Navigation */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-300">Step-by-Step Viewer</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={prev}
            disabled={step === 0}
            className="px-2 py-1 rounded text-xs font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs font-mono text-zinc-400 min-w-[80px] text-center">
            {step + 1} / {events.length}
          </span>
          <button
            onClick={next}
            disabled={step === events.length - 1}
            className="px-2 py-1 rounded text-xs font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-zinc-800">
        <div
          className="h-full bg-emerald-500 transition-all duration-200"
          style={{ width: `${((step + 1) / events.length) * 100}%` }}
        />
      </div>

      {/* Turn header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-3">
        <span className="text-xs font-mono text-zinc-500">Turn {ev.turn_number}</span>
        <span
          className={`text-xs font-medium px-1.5 py-0.5 rounded ${
            ev.agent_id === "agent_a"
              ? "bg-blue-500/10 text-blue-400"
              : "bg-orange-500/10 text-orange-400"
          }`}
        >
          {ev.agent_id === "agent_a" ? "Agent A" : "Agent B"}
        </span>
        <span className="text-xs text-zinc-500">
          Action: <code className="text-zinc-300">{ev.chosen_action}</code>
        </span>
        <span
          className={`text-xs px-1.5 py-0.5 rounded ${
            result.success
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400"
          }`}
        >
          {result.success ? "OK" : "FAIL"}
        </span>

        {ev.discrepancy_detected && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">
            ⚠ Discrepancy
          </span>
        )}
      </div>

      {/* Discrepancy banner */}
      {ev.discrepancy_detected && ev.discrepancy_details && (
        <div className="mx-4 mt-3 p-3 bg-red-500/5 border border-red-500/20 rounded-md">
          <p className="text-xs font-semibold text-red-400 mb-1">⚠ Discrepancy</p>
          <p className="text-xs text-red-300/80 leading-relaxed">{ev.discrepancy_details}</p>
        </div>
      )}

      {/* DM Oracle */}
      {ev.dm_query && (
        <div className="mx-4 mt-3 p-3 bg-purple-500/5 border border-purple-500/20 rounded-md">
          <p className="text-xs font-semibold text-purple-400 mb-1">
            🔮 DM Oracle
            {ev.dm_stale_turns_count !== null && ev.dm_stale_turns_count > 0 && (
              <span className="ml-2 text-amber-400 font-normal">
                ({ev.dm_stale_turns_count} turns stale)
              </span>
            )}
          </p>
          <p className="text-xs text-zinc-400">Q: &quot;{ev.dm_query}&quot;</p>
          {ev.dm_advice && (
            <p className="text-xs text-purple-300/80 mt-1">A: &quot;{ev.dm_advice}&quot;</p>
          )}
        </div>
      )}

      {/* Split: Belief vs Reality */}
      <div className="grid grid-cols-2 gap-px bg-zinc-800 mt-3">
        {/* Left: Belief */}
        <div className="bg-zinc-900 p-4">
          <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-3">
            Agent&apos;s Belief
          </h4>
          <Row label="Position" value={`(${obs.agent_position[0]}, ${obs.agent_position[1]})`} />
          <Row label="Has Key" value={belief.has_key ? "Yes" : "No"} />
          <Row
            label="Key Location"
            value={belief.key_location ? `(${belief.key_location[0]}, ${belief.key_location[1]})` : "Unknown"}
          />
          <Row
            label="Partner Location"
            value={belief.partner_location ? `(${belief.partner_location[0]}, ${belief.partner_location[1]})` : "Unknown"}
          />
          <Row label="Known cells" value={String(Object.keys(belief.grid_knowledge).length)} />
          <div className="mt-3">
            <MiniGrid knowledge={belief.grid_knowledge} agentPos={obs.agent_position} />
          </div>
        </div>

        {/* Right: Reality */}
        <div className="bg-zinc-900 p-4">
          <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wide mb-3">
            Actual World
          </h4>
          <Row label="Position" value={`(${obs.agent_position[0]}, ${obs.agent_position[1]})`} />
          <Row label="Current Cell" value={obs.current_cell} />
          <Row label="Has Key" value={obs.has_key ? "Yes" : "No"} />
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
        </div>
      </div>

      {/* Result */}
      <div className="px-4 py-3 border-t border-zinc-800">
        <p className="text-xs text-zinc-400">
          <span className="text-zinc-500">Result:</span> {result.message}
        </p>
      </div>

      {/* Keyboard hint */}
      <div className="px-4 py-2 border-t border-zinc-800">
        <p className="text-xs text-zinc-600 text-center">
          Use ← → keys or buttons to navigate steps
        </p>
      </div>
    </div>
  );
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-xs font-mono text-zinc-300">{value}</span>
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
  const cells = Object.entries(knowledge);
  if (cells.length === 0) return <p className="text-xs text-zinc-600">No cells explored</p>;

  let minR = Infinity, maxR = -Infinity, minC = Infinity, maxC = -Infinity;
  for (const [key] of cells) {
    const [r, c] = key.split(",").map(Number);
    minR = Math.min(minR, r);
    maxR = Math.max(maxR, r);
    minC = Math.min(minC, c);
    maxC = Math.max(maxC, c);
  }

  const rows = Math.min(maxR - minR + 1, 12);
  const cols = Math.min(maxC - minC + 1, 12);

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
