"use client";

import { useEffect, useState } from "react";
import { fetchRuns } from "@/lib/api";
import type { RunSummary } from "@/lib/api";

interface Props {
  currentRunId: string | null;
  onSelect: (runId: string) => void;
}

export function RunSelector({ currentRunId, onSelect }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetchRuns().then(setRuns).catch(() => {});
  }, []);

  // Refresh when a new run gets selected (i.e. after simulation completes)
  useEffect(() => {
    if (currentRunId) {
      fetchRuns().then(setRuns).catch(() => {});
    }
  }, [currentRunId]);

  if (runs.length <= 1) return null;

  const current = runs.find((r) => r.run_id === currentRunId);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:border-slate-600 text-sm text-zinc-300 transition-colors"
      >
        <span className="text-zinc-500">Run:</span>
        <span className="font-medium truncate max-w-[160px]">
          {current?.label ?? currentRunId?.slice(0, 8) ?? "—"}
        </span>
        <span className="text-zinc-600">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div className="absolute top-full mt-1 right-0 z-50 bg-slate-900 border border-slate-700 rounded-lg shadow-xl min-w-[280px] max-h-[320px] overflow-y-auto">
          {runs.map((run) => (
            <button
              key={run.run_id}
              onClick={() => {
                onSelect(run.run_id);
                setOpen(false);
              }}
              className={`w-full text-left px-3 py-2 flex items-center gap-3 hover:bg-slate-800 transition-colors ${
                run.run_id === currentRunId ? "bg-slate-800" : ""
              }`}
            >
              {/* Win/Loss badge */}
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  run.win ? "bg-emerald-400" : "bg-red-400"
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-zinc-200 truncate">
                    {run.label}
                  </span>
                  <span className="text-xs text-zinc-600">
                    {run.source === "demo" ? "demo" : "live"}
                  </span>
                </div>
                <div className="text-xs text-zinc-500">
                  {run.grid_size} · {run.total_turns} turns · DM lag {run.dm_stale_turns}
                </div>
              </div>
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  run.win
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-red-500/10 text-red-400"
                }`}
              >
                {run.win ? "WIN" : "LOSS"}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
