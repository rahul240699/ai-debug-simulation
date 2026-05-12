"use client";

import { useEffect, useRef } from "react";
import type { EventRecord } from "@/lib/types";

interface Props {
  events: EventRecord[];
  highlightTurn?: number | null;
}

export function ReasoningStream({ events, highlightTurn }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to highlighted turn
  useEffect(() => {
    if (highlightTurn !== null && highlightTurn !== undefined) {
      const el = document.getElementById(`reasoning-t${highlightTurn}`);
      if (el && containerRef.current) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [highlightTurn]);

  if (events.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Agent Reasoning Stream</h3>
        <p className="text-xs text-zinc-600">No reasoning traces available</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg flex flex-col">
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <h3 className="text-sm font-semibold text-zinc-300">Agent Reasoning Stream</h3>
        <span className="text-xs text-zinc-600 ml-auto">{events.length} traces</span>
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto max-h-[600px] font-mono text-xs"
      >
        {events.map((ev, i) => {
          const isHighlighted = highlightTurn === ev.turn_number;
          const isAgent_a = ev.agent_id === "agent_a";

          return (
            <div
              key={`${ev.turn_number}-${ev.agent_id}-${i}`}
              id={`reasoning-t${ev.turn_number}`}
              className={`px-4 py-2 border-b border-slate-700/20 transition-colors duration-300 ${
                isHighlighted ? "bg-slate-700/50" : "hover:bg-slate-700/20"
              }`}
            >
              {/* Header */}
              <div className="flex items-center gap-2 mb-1">
                <span className="text-zinc-600">[T{String(ev.turn_number).padStart(2, "0")}]</span>
                <span className={isAgent_a ? "text-blue-400" : "text-orange-400"}>
                  {isAgent_a ? "A" : "B"}
                </span>
                <span className="text-zinc-500">→</span>
                <span className="text-emerald-400">{ev.chosen_action}</span>
                {!ev.action_result.success && (
                  <span className="text-rose-400">FAIL</span>
                )}
                {ev.discrepancy_detected && (
                  <span className="text-rose-400">⚠</span>
                )}
              </div>

              {/* Rationale */}
              {ev.rationale && (
                <p className="text-zinc-400 leading-relaxed pl-6 whitespace-pre-wrap">
                  {ev.rationale}
                </p>
              )}

              {/* DM query inline */}
              {ev.dm_query && (
                <p className="text-purple-400/70 pl-6 mt-0.5">
                  ↳ DM: &quot;{ev.dm_advice?.slice(0, 100)}&quot;
                  {ev.dm_stale_turns_count ? ` [${ev.dm_stale_turns_count}t stale]` : ""}
                </p>
              )}

              {/* Discrepancy inline */}
              {ev.discrepancy_details && (
                <p className="text-rose-400/70 pl-6 mt-0.5">
                  ↳ {ev.discrepancy_details.slice(0, 120)}
                </p>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
